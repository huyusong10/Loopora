from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from loopora.engine.advance_policy import RunnerStepSelection, RunnerStepSelectionRequest, select_next_runner_step
from loopora.engine.run_requests import RunEngineClaimRunnerStepRequest
from loopora.engine.step_instruction import RunnerStepInstructionRequest, runner_step_instruction
from loopora.kernel import ActorRef
from loopora.recovery import RetryConfig
from loopora.run_artifacts import read_jsonl


class RunnerStepCursor(Protocol):
    def runner_step_index(
        self,
        run_id: str,
        *,
        strategy_steps: list[dict],
        iteration: int,
        fallback_step_index: int = 0,
    ) -> int: ...


def evidence_context_with_canonical_items(step_instruction_context: dict, layout: object) -> dict:
    evidence_context = (
        step_instruction_context.get("evidence") if isinstance(step_instruction_context.get("evidence"), dict) else {}
    )
    known_ids = {str(item).strip() for item in list(evidence_context.get("known_ids") or []) if str(item).strip()}
    current_items = [item for item in list(evidence_context.get("items") or []) if isinstance(item, dict)]
    current_ids = {str(item.get("id") or "").strip() for item in current_items if str(item.get("id") or "").strip()}
    if not known_ids or known_ids.issubset(current_ids):
        return dict(evidence_context)
    canonical_items = [item for item in read_jsonl(layout.evidence_ledger_path) if isinstance(item, dict) and str(item.get("id") or "").strip() in known_ids]
    return {**dict(evidence_context), "items": canonical_items}


def runner_step_claim_request(
    context: RunnerRunContext,
    iteration: RunnerIterationState,
    *,
    step: dict,
    role: dict,
    pending_actor: ActorRef,
) -> RunEngineClaimRunnerStepRequest:
    return RunEngineClaimRunnerStepRequest(
        instruction=runner_step_instruction(
            RunnerStepInstructionRequest(
                run_id=context.run_id,
                contract_ref=str(context.layout.run_contract_path),
                compiled_spec=context.compiled_spec,
                iteration=iteration.iter_id,
                step=step,
                role=role,
            )
        ),
        pending_actor=pending_actor,
    )


@dataclass(frozen=True)
class RunnerStepClaimPlan:
    step_order: int
    step: dict
    role: dict
    parallel_group: str
    claim_request: RunEngineClaimRunnerStepRequest


@dataclass(frozen=True)
class RunnerParallelGroupClaimPlan:
    parallel_group: str
    group_start: int
    next_step_index: int
    steps: tuple[RunnerStepClaimPlan, ...]


def runner_step_claim_plan(
    run_engine: RunnerStepCursor,
    context: RunnerRunContext,
    iteration: RunnerIterationState,
    *,
    pending_actor: ActorRef,
    fallback_step_index: int = 0,
) -> RunnerStepClaimPlan | None:
    step_index = run_engine.runner_step_index(
        context.run_id,
        strategy_steps=context.strategy_steps,
        iteration=iteration.iter_id,
        fallback_step_index=fallback_step_index,
    )
    selection = select_next_runner_step(RunnerStepSelectionRequest(context.strategy_steps, step_index))
    if selection is None:
        return None
    return _runner_step_claim_plan_from_selection(context, iteration, selection, pending_actor=pending_actor)


def runner_parallel_group_claim_plan(
    context: RunnerRunContext,
    iteration: RunnerIterationState,
    *,
    first_plan: RunnerStepClaimPlan,
    pending_actor: ActorRef,
) -> RunnerParallelGroupClaimPlan:
    parallel_group = first_plan.parallel_group
    step_index = first_plan.step_order
    group_steps: list[RunnerStepClaimPlan] = []
    while (
        step_index < len(context.strategy_steps)
        and str(context.strategy_steps[step_index].get("parallel_group") or "").strip() == parallel_group
    ):
        selection = select_next_runner_step(RunnerStepSelectionRequest(context.strategy_steps, step_index))
        if selection is None:
            break
        group_steps.append(
            _runner_step_claim_plan_from_selection(
                context,
                iteration,
                selection,
                pending_actor=pending_actor,
            )
        )
        step_index = selection.step_order + 1
    return RunnerParallelGroupClaimPlan(
        parallel_group=parallel_group,
        group_start=first_plan.step_order,
        next_step_index=step_index,
        steps=tuple(group_steps),
    )


def _runner_step_claim_plan_from_selection(
    context: RunnerRunContext,
    iteration: RunnerIterationState,
    selection: RunnerStepSelection,
    *,
    pending_actor: ActorRef,
) -> RunnerStepClaimPlan:
    step = dict(selection.step)
    role = context.role_by_id[str(step["role_id"])]
    return RunnerStepClaimPlan(
        step_order=selection.step_order,
        step=step,
        role=role,
        parallel_group=selection.parallel_group,
        claim_request=runner_step_claim_request(
            context,
            iteration,
            step=step,
            role=role,
            pending_actor=pending_actor,
        ),
    )


@dataclass
class RunnerRunContext:
    run_id: str
    run: dict
    run_dir: Path
    strategy_source: dict
    executor: object
    compiled_spec: dict
    retry_config: RetryConfig
    prompt_files: dict[str, str]
    layout: object
    run_contract: dict
    strategy_steps: list[dict]
    strategy_controls: list[dict]
    control_fire_counts: dict[str, int]
    runner_started_at: float
    role_by_id: dict[str, dict]
    completion_mode: str
    last_gatekeeper_result: dict | None = None


@dataclass
class RunnerIterationState:
    iter_id: int
    previous_composite: object
    stagnation: dict
    previous_outputs_by_step: dict[str, dict]
    previous_outputs_by_role: dict[str, dict]
    previous_outputs_by_archetype: dict[str, dict]
    previous_handoffs_by_step: dict[str, dict]
    previous_handoffs_by_role: dict[str, dict]
    previous_iteration_summary: dict | None
    previous_session_refs_by_step: dict[str, dict]
    step_results: list[dict] = field(default_factory=list)
    current_outputs_by_step: dict[str, dict] = field(default_factory=dict)
    current_outputs_by_role: dict[str, dict] = field(default_factory=dict)
    current_outputs_by_archetype: dict[str, dict] = field(default_factory=dict)
    current_handoffs: list[dict] = field(default_factory=list)
    current_session_refs_by_step: dict[str, dict] = field(default_factory=dict)
    current_gatekeeper_result: dict | None = None
    current_guide_result: dict | None = None

    def snapshot(self) -> dict[str, object]:
        return {
            "current_outputs_by_step": dict(self.current_outputs_by_step),
            "current_outputs_by_role": dict(self.current_outputs_by_role),
            "current_outputs_by_archetype": dict(self.current_outputs_by_archetype),
            "current_handoffs": list(self.current_handoffs),
        }
