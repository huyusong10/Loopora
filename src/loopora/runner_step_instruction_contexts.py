from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.context_flow import (
    StepInstructionContextRequest,
    build_step_instruction_context,
)
from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection
from loopora.run_artifacts import read_jsonl
from loopora.runner_step_context_inputs import (
    dedupe_evidence_items,
    evidence_known_ids as known_evidence_ids,
    filter_evidence_for_step,
    filter_handoffs_for_step,
    iteration_memory_for_step,
    manifest_prompt_context,
    merge_coverage_gap_evidence,
    step_declares_evidence_query,
)
from loopora.runner_step_runtime import RunnerStepRuntimeRequest
from loopora.utils import write_json


@dataclass(frozen=True)
class RunnerStepInstructionContextPreparation:
    step_instruction_context: dict
    context_path: Path
    current_handoffs_for_step: list[dict]
    previous_iteration_summary_for_step: dict | None


def prepare_runner_step_instruction_context(
    request: RunnerStepRuntimeRequest,
) -> RunnerStepInstructionContextPreparation:
    runtime_request = request
    layout = runtime_request.layout
    iter_id = runtime_request.iter_id
    step = runtime_request.step
    step_order = runtime_request.step_order
    role = runtime_request.role
    all_evidence_items = (
        list(runtime_request.evidence_items_snapshot)
        if runtime_request.evidence_items_snapshot is not None
        else read_jsonl(layout.evidence_ledger_path)
    )
    all_evidence_items = dedupe_evidence_items(all_evidence_items)
    current_handoffs_for_step = filter_handoffs_for_step(step, runtime_request.current_handoffs)
    (
        previous_iteration_same_step_for_step,
        previous_iteration_same_role_for_step,
        previous_iteration_summary_for_step,
    ) = iteration_memory_for_step(
        step,
        previous_iteration_same_step=runtime_request.previous_handoffs_by_step.get(step["id"]),
        previous_iteration_same_role=runtime_request.previous_handoffs_by_role.get(role["id"]),
        previous_iteration_summary=runtime_request.previous_iteration_summary,
    )
    declares_evidence_query = step_declares_evidence_query(step)
    evidence_items = filter_evidence_for_step(step, all_evidence_items) if declares_evidence_query else all_evidence_items[-40:]
    evidence_coverage_summary = summarize_evidence_coverage_projection(
        load_or_build_evidence_coverage_projection(layout),
        coverage_path_available=layout.evidence_coverage_path.exists(),
    )
    evidence_items, evidence_known_ids = merge_coverage_gap_evidence(
        evidence_items,
        all_evidence_items=all_evidence_items,
        coverage_summary=evidence_coverage_summary,
    )
    if not declares_evidence_query:
        evidence_known_ids = known_evidence_ids(all_evidence_items)
    evidence_manifest_summary, evidence_manifest_claims = manifest_prompt_context(layout, evidence_known_ids)
    step_instruction_context = build_step_instruction_context(
        StepInstructionContextRequest(
            run_contract=runtime_request.run_contract,
            layout=layout,
            iter_id=iter_id,
            step=step,
            step_order=step_order,
            role=role,
            execution_settings=runtime_request.execution_settings,
            immediate_previous_step=current_handoffs_for_step[-1] if current_handoffs_for_step else None,
            completed_steps_this_iteration=current_handoffs_for_step,
            previous_iteration_same_step=previous_iteration_same_step_for_step,
            previous_iteration_same_role=previous_iteration_same_role_for_step,
            previous_iteration_summary=previous_iteration_summary_for_step,
            previous_composite=runtime_request.previous_composite,
            stagnation_mode=runtime_request.stagnation_mode,
            evidence_progress_mode=runtime_request.evidence_progress_mode,
            covered_check_count=runtime_request.covered_check_count,
            missing_check_count=runtime_request.missing_check_count,
            consecutive_no_required_coverage_delta=runtime_request.consecutive_no_required_coverage_delta,
            evidence_coverage_summary=evidence_coverage_summary,
            evidence_items=evidence_items,
            evidence_known_ids=evidence_known_ids,
            evidence_manifest_summary=evidence_manifest_summary,
            evidence_manifest_claims=evidence_manifest_claims,
            continuation_context=runtime_request.run_contract.get("continuation_context")
            if isinstance(runtime_request.run_contract, dict)
            else None,
        )
    )
    context_path = layout.step_instruction_context_path(iter_id, step_order, step["id"])
    write_json(context_path, step_instruction_context)
    return RunnerStepInstructionContextPreparation(
        step_instruction_context=step_instruction_context,
        context_path=context_path,
        current_handoffs_for_step=current_handoffs_for_step,
        previous_iteration_summary_for_step=previous_iteration_summary_for_step,
    )
