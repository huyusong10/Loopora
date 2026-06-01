from __future__ import annotations

from dataclasses import dataclass

from loopora.context_contract_snapshot import (
    RunContractSnapshotRequest as RunContractSnapshotRequest,
    build_run_contract_snapshot as build_run_contract_snapshot,
    contract_mapping_list as _contract_mapping_list,
    contract_role_postures as _contract_role_postures,
    contract_string as _contract_string,
    contract_string_list as _contract_string_list,
)
from loopora.context_iteration_summary import (
    IterationSummaryContext as IterationSummaryContext,
    build_iteration_summary as build_iteration_summary,
    derive_latest_state as derive_latest_state,
)
from loopora.context_prompt_contracts import (
    _combine_role_guidance as _combine_role_guidance,
    output_contract_prompt as output_contract_prompt,
    render_role_note_section as render_role_note_section,
    render_run_contract_section as render_run_contract_section,
    render_step_prompt as render_step_prompt,
    system_prompt_prefix as system_prompt_prefix,
)
from loopora.context_prompt_sections import (
    render_artifact_refs as render_artifact_refs,
    render_continuation_section as render_continuation_section,
    render_evidence_section as render_evidence_section,
    render_handoff_list_section as render_handoff_list_section,
    render_handoff_section as render_handoff_section,
    render_iteration_section as render_iteration_section,
    render_previous_iteration_summary as render_previous_iteration_summary,
)
from loopora.context_step_results import (
    StepEvidenceEntryRequest as StepEvidenceEntryRequest,
    StepResultContext as StepResultContext,
    build_step_evidence_entry as build_step_evidence_entry,
    build_step_handoff as build_step_handoff,
    evidence_entry_id as evidence_entry_id,
)
from loopora.context_schemas import (
    ARTIFACT_REF_SCHEMA as ARTIFACT_REF_SCHEMA,
    EVIDENCE_COVERAGE_GAP_SCHEMA as EVIDENCE_COVERAGE_GAP_SCHEMA,
    EVIDENCE_COVERAGE_RESULT_SCHEMA as EVIDENCE_COVERAGE_RESULT_SCHEMA,
    EVIDENCE_ITEM_SCHEMA as EVIDENCE_ITEM_SCHEMA,
    EVIDENCE_MANIFEST_CLAIM_SCHEMA as EVIDENCE_MANIFEST_CLAIM_SCHEMA,
    EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA as EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA,
    EVIDENCE_MANIFEST_SUMMARY_SCHEMA as EVIDENCE_MANIFEST_SUMMARY_SCHEMA,
    ITERATION_SUMMARY_SCHEMA as ITERATION_SUMMARY_SCHEMA,
    LATEST_STATE_SCHEMA as LATEST_STATE_SCHEMA,
    ROLE_POSTURE_CONTRACT_SCHEMA as ROLE_POSTURE_CONTRACT_SCHEMA,
    STEP_HANDOFF_SCHEMA as STEP_HANDOFF_SCHEMA,
    STEP_INSTRUCTION_CONTEXT_SCHEMA as STEP_INSTRUCTION_CONTEXT_SCHEMA,
    TASK_VERDICT_BUCKETS_SCHEMA as TASK_VERDICT_BUCKETS_SCHEMA,
    TASK_VERDICT_CONTEXT_SCHEMA as TASK_VERDICT_CONTEXT_SCHEMA,
)
from loopora.context_step_instruction_normalizers import (
    int_value as _int_value,
    normalize_continuation_context as _normalize_continuation_context,
    normalize_evidence_coverage_summary as _normalize_evidence_coverage_summary,
    normalize_evidence_items as _normalize_evidence_items,
    normalize_manifest_claims as _normalize_manifest_claims,
    normalize_manifest_claim_coverage_targets as normalize_manifest_claim_coverage_targets,
    normalize_manifest_summary as _normalize_manifest_summary,
)
from loopora.run_artifacts import RunArtifactLayout, artifact_ref
from loopora.service_bundle_control_trace_mining import (
    build_execution_strategy_trace,
    build_judgment_tradeoff_trace,
    build_loop_fit_trace,
    build_runtime_local_governance_trace,
)
from loopora.structured_numbers import coerced_non_negative_int


@dataclass(frozen=True)
class StepInstructionContextRequest:
    run_contract: dict
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    execution_settings: dict[str, str]
    immediate_previous_step: dict | None
    completed_steps_this_iteration: list[dict]
    previous_iteration_same_step: dict | None
    previous_iteration_same_role: dict | None
    previous_iteration_summary: dict | None
    previous_composite: float | None
    stagnation_mode: str
    evidence_progress_mode: str = "none"
    covered_check_count: int = 0
    missing_check_count: int = 0
    consecutive_no_required_coverage_delta: int = 0
    evidence_coverage_summary: dict | None = None
    evidence_items: list[dict] | None = None
    evidence_known_ids: list[str] | None = None
    evidence_manifest_summary: dict | None = None
    evidence_manifest_claims: list[dict] | None = None
    continuation_context: dict | None = None


def build_step_instruction_context(request: StepInstructionContextRequest) -> dict:
    run_contract = request.run_contract
    layout = request.layout
    step = request.step
    role = request.role
    compiled_spec = run_contract.get("compiled_spec") or {}
    strategy_snapshot = run_contract.get("workflow") or {}
    raw_sections = compiled_spec.get("raw_sections") if isinstance(compiled_spec.get("raw_sections"), dict) else {}
    strategy_roles = strategy_snapshot.get("roles") if isinstance(strategy_snapshot.get("roles"), list) else []
    coverage_summary = _normalize_evidence_coverage_summary(
        request.evidence_coverage_summary,
        fallback_covered_check_count=request.covered_check_count,
        fallback_missing_check_count=request.missing_check_count,
    )
    judgment_tradeoffs = _contract_string_list(run_contract.get("judgment_tradeoffs")) or build_judgment_tradeoff_trace(
        collaboration_summary=run_contract.get("collaboration_summary"),
        raw_sections=raw_sections,
        roles=strategy_roles,
        strategy_source=strategy_snapshot,
    )
    execution_strategy = _contract_string_list(run_contract.get("execution_strategy")) or build_execution_strategy_trace(
        collaboration_summary=run_contract.get("collaboration_summary"),
        raw_sections=raw_sections,
        roles=strategy_roles,
        strategy_source=strategy_snapshot,
    )
    local_governance = _contract_string_list(run_contract.get("local_governance")) or build_runtime_local_governance_trace(
        raw_sections=raw_sections,
        roles=strategy_roles,
        strategy_source=strategy_snapshot,
    )
    continuation_context = _normalize_continuation_context(request.continuation_context or run_contract.get("continuation_context"))
    iter_index = coerced_non_negative_int(request.iter_id)
    step_order = coerced_non_negative_int(request.step_order)
    return {
        "contract": {
            "path": layout.relative(layout.run_contract_path),
            "goal": str(compiled_spec.get("goal") or "").strip(),
            "constraints": str(compiled_spec.get("constraints") or "No explicit constraints were provided.").strip(),
            "check_mode": str(compiled_spec.get("check_mode") or "specified"),
            "check_count": len(compiled_spec.get("checks") or []),
            "completion_mode": str(run_contract.get("completion_mode") or "gatekeeper"),
            "collaboration_summary": str(run_contract.get("collaboration_summary") or "").strip(),
            "loop_fit_reasons": _contract_string_list(run_contract.get("loop_fit_reasons")) or build_loop_fit_trace(
                run_contract.get("collaboration_summary")
            ),
            "strategy_preset": str(strategy_snapshot.get("preset") or "custom"),
            "strategy_collaboration_intent": str(strategy_snapshot.get("collaboration_intent") or "").strip(),
            "judgment_tradeoffs": judgment_tradeoffs,
            "execution_strategy": execution_strategy,
            "local_governance": local_governance,
            "role_postures": _contract_role_postures(run_contract.get("role_postures") or strategy_snapshot.get("roles")),
            "coverage_targets": _contract_mapping_list(compiled_spec.get("coverage_targets")),
            "success_surface": _contract_string_list(run_contract.get("success_surface") or compiled_spec.get("success_surface")),
            "fake_done_states": _contract_string_list(run_contract.get("fake_done_states") or compiled_spec.get("fake_done_states")),
            "evidence_preferences": _contract_string_list(run_contract.get("evidence_preferences") or compiled_spec.get("evidence_preferences")),
            "residual_risk": _contract_string(run_contract.get("residual_risk") or compiled_spec.get("residual_risk")),
        },
        "continuation": continuation_context,
        "iteration": {
            "iter_index": iter_index,
            "is_first_iteration": iter_index == 0,
            "previous_iteration_exists": iter_index > 0,
            "previous_composite": request.previous_composite,
            "stagnation_mode": str(request.stagnation_mode or "none"),
            "evidence_progress_mode": str(request.evidence_progress_mode or "none"),
            "coverage_status": coverage_summary["status"],
            "covered_check_count": coverage_summary["covered_check_count"],
            "missing_check_count": coverage_summary["missing_check_count"],
            "covered_check_ids": coverage_summary["covered_check_ids"],
            "missing_check_ids": coverage_summary["missing_check_ids"],
            "target_count": coverage_summary["target_count"],
            "covered_target_count": coverage_summary["covered_target_count"],
            "weak_target_count": coverage_summary["weak_target_count"],
            "missing_target_count": coverage_summary["missing_target_count"],
            "blocked_target_count": coverage_summary["blocked_target_count"],
            "coverage_top_gaps": coverage_summary["top_gaps"],
            "consecutive_no_required_coverage_delta": _int_value(request.consecutive_no_required_coverage_delta),
        },
        "current_step": {
            "step_id": str(step["id"]),
            "step_order": step_order,
            "role_id": str(role["id"]),
            "role_name": str(role["name"]),
            "archetype": str(role["archetype"]),
            "model": str(request.execution_settings.get("model") or ""),
            "executor_kind": str(request.execution_settings.get("executor_kind") or ""),
            "executor_mode": str(request.execution_settings.get("executor_mode") or ""),
            "parallel_group": str(step.get("parallel_group") or ""),
            "inputs": dict(step.get("inputs") or {}),
            "action_policy": dict(step.get("action_policy") or {}),
            "control": dict(step.get("control") or {}) if isinstance(step.get("control"), dict) else {},
        },
        "upstream": {
            "immediate_previous_step": request.immediate_previous_step,
            "completed_steps_this_iteration": list(request.completed_steps_this_iteration),
            "previous_iteration_same_step": request.previous_iteration_same_step,
            "previous_iteration_same_role": request.previous_iteration_same_role,
            "previous_iteration_summary": request.previous_iteration_summary,
        },
        "evidence": {
            "ledger_path": layout.relative(layout.evidence_ledger_path),
            "manifest_path": layout.relative(layout.evidence_manifest_path),
            "coverage_path": layout.relative(layout.evidence_coverage_path),
            "items": _normalize_evidence_items(request.evidence_items),
            "known_ids": list(request.evidence_known_ids or []),
            "manifest_summary": _normalize_manifest_summary(request.evidence_manifest_summary),
            "manifest_claims": _normalize_manifest_claims(request.evidence_manifest_claims),
        },
        "artifacts": [
            artifact_ref(layout, layout.run_contract_path, kind="contract", label="run-contract"),
            artifact_ref(layout, layout.latest_state_path, kind="state", label="latest-state"),
            artifact_ref(layout, layout.latest_iteration_summary_path, kind="state", label="latest-iteration-summary"),
            artifact_ref(layout, layout.timeline_events_path, kind="timeline", label="timeline-events"),
            artifact_ref(layout, layout.timeline_iterations_path, kind="timeline", label="timeline-iterations"),
            artifact_ref(layout, layout.timeline_metrics_path, kind="timeline", label="timeline-metrics"),
            artifact_ref(layout, layout.evidence_ledger_path, kind="evidence", label="evidence-ledger"),
            artifact_ref(layout, layout.evidence_coverage_path, kind="evidence", label="evidence-coverage"),
            artifact_ref(layout, layout.evidence_manifest_path, kind="evidence", label="evidence-manifest"),
        ],
    }
