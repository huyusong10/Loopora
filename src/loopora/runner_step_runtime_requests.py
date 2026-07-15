from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext
from loopora.utils import structured_non_negative_int


from loopora.executor_types import CodexExecutor

from loopora.recovery import RetryConfig

from loopora.run_artifacts import RunArtifactLayout

@dataclass(frozen=True)
class RunnerStepRuntimeRequest:
    executor: CodexExecutor
    run: dict
    compiled_spec: dict
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    prompt_files: dict[str, str]
    execution_settings: dict[str, object]
    run_contract: dict
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_handoffs: list[dict]
    previous_outputs_by_step: dict[str, dict]
    previous_outputs_by_role: dict[str, dict]
    previous_outputs_by_archetype: dict[str, dict]
    previous_handoffs_by_step: dict[str, dict]
    previous_handoffs_by_role: dict[str, dict]
    previous_iteration_summary: dict | None
    previous_session_refs_by_step: dict[str, dict]
    previous_composite: float | None
    stagnation_mode: str
    evidence_progress_mode: str
    covered_check_count: int
    missing_check_count: int
    consecutive_no_required_coverage_delta: int
    retry_config: RetryConfig
    evidence_items_snapshot: list[dict] | None = None


@dataclass(frozen=True)
class RunnerStepRuntimeInputSnapshot:
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_handoffs: list[dict]
    evidence_items_snapshot: list[dict] | None = None


@dataclass(frozen=True)
class RunnerStepRuntimeRequestBuildRequest:
    context: RunnerRunContext
    iteration: RunnerIterationState
    run: dict
    step: dict
    step_order: int
    role: dict
    execution_settings: dict[str, object]
    input_snapshot: RunnerStepRuntimeInputSnapshot


def runner_step_runtime_input_snapshot_from_mapping(snapshot: dict[str, Any]) -> RunnerStepRuntimeInputSnapshot:
    return RunnerStepRuntimeInputSnapshot(
        current_outputs_by_step=dict(snapshot["current_outputs_by_step"]),
        current_outputs_by_role=dict(snapshot["current_outputs_by_role"]),
        current_outputs_by_archetype=dict(snapshot["current_outputs_by_archetype"]),
        current_handoffs=list(snapshot["current_handoffs"]),
    )


def build_runner_step_runtime_request(
    request: RunnerStepRuntimeRequestBuildRequest,
) -> RunnerStepRuntimeRequest:
    context = request.context
    iteration = request.iteration
    input_snapshot = request.input_snapshot
    return RunnerStepRuntimeRequest(
        executor=context.executor,
        run=request.run,
        compiled_spec=context.compiled_spec,
        layout=context.layout,
        iter_id=iteration.iter_id,
        step=request.step,
        step_order=request.step_order,
        role=request.role,
        prompt_files=context.prompt_files,
        execution_settings=request.execution_settings,
        run_contract=context.run_contract,
        current_outputs_by_step=dict(input_snapshot.current_outputs_by_step),
        current_outputs_by_role=dict(input_snapshot.current_outputs_by_role),
        current_outputs_by_archetype=dict(input_snapshot.current_outputs_by_archetype),
        current_handoffs=list(input_snapshot.current_handoffs),
        previous_outputs_by_step=iteration.previous_outputs_by_step,
        previous_outputs_by_role=iteration.previous_outputs_by_role,
        previous_outputs_by_archetype=iteration.previous_outputs_by_archetype,
        previous_handoffs_by_step=iteration.previous_handoffs_by_step,
        previous_handoffs_by_role=iteration.previous_handoffs_by_role,
        previous_iteration_summary=iteration.previous_iteration_summary,
        previous_session_refs_by_step=iteration.previous_session_refs_by_step,
        previous_composite=iteration.previous_composite,
        stagnation_mode=iteration.stagnation.get("stagnation_mode", "none"),
        evidence_progress_mode=iteration.stagnation.get("evidence_progress_mode", "none"),
        covered_check_count=structured_non_negative_int(iteration.stagnation.get("latest_covered_check_count")),
        missing_check_count=structured_non_negative_int(iteration.stagnation.get("latest_missing_check_count")),
        consecutive_no_required_coverage_delta=structured_non_negative_int(
            iteration.stagnation.get("consecutive_no_required_coverage_delta")
        ),
        retry_config=context.retry_config,
        evidence_items_snapshot=(
            list(input_snapshot.evidence_items_snapshot) if input_snapshot.evidence_items_snapshot is not None else None
        ),
    )
