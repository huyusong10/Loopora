from __future__ import annotations

from dataclasses import dataclass

from loopora.context_value_helpers import clean_text as _clean_text
from loopora.context_value_helpers import evidence_coverage_results as _evidence_coverage_results
from loopora.context_value_helpers import gatekeeper_blockers as _gatekeeper_blockers
from loopora.context_value_helpers import normalize_coverage_gap_rows as _normalize_coverage_gap_rows
from loopora.context_value_helpers import string_list as _string_list
from loopora.run_artifacts import RunArtifactLayout
from loopora.score_history_values import structured_score_value, structured_score_values
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import coerced_non_negative_int, structured_non_negative_int


@dataclass(frozen=True)
class IterationSummaryContext:
    layout: RunArtifactLayout
    iter_id: int
    step_results: list[dict]
    stagnation: dict
    previous_composite: float | None
    timestamp: str


def build_iteration_summary(context: IterationSummaryContext) -> dict:
    layout = context.layout
    iter_id = coerced_non_negative_int(context.iter_id)
    step_results = context.step_results
    stagnation = context.stagnation
    gatekeeper_handoff = next(
        (item["handoff"] for item in reversed(step_results) if item["role"]["archetype"] == "gatekeeper"),
        None,
    )
    gatekeeper_output = next(
        (item["output"] for item in reversed(step_results) if item["role"]["archetype"] == "gatekeeper"),
        {},
    )
    latest_by_step = {
        item["step"]["id"]: layout.relative(
            layout.step_handoff_path(iter_id, coerced_non_negative_int(item["step_order"]), item["step"]["id"])
        )
        for item in step_results
    }
    latest_by_role = {
        item["role"]["id"]: layout.relative(
            layout.step_handoff_path(iter_id, coerced_non_negative_int(item["step_order"]), item["step"]["id"])
        )
        for item in step_results
    }
    latest_by_archetype = {
        item["role"]["archetype"]: layout.relative(
            layout.step_handoff_path(iter_id, coerced_non_negative_int(item["step_order"]), item["step"]["id"])
        )
        for item in step_results
    }
    composite = _number_value(gatekeeper_output.get("composite_score"))
    previous_composite = _number_value(context.previous_composite)
    delta = round(composite - previous_composite, 6) if composite is not None and previous_composite is not None else None
    return {
        "phase": "complete",
        "iter": iter_id,
        "timestamp": context.timestamp,
        "workflow": [
            {
                "step_id": str(item["step"]["id"]),
                "role_id": str(item["role"]["id"]),
                "role_name": str(item["role"]["name"]),
                "runtime_role": str(item["runtime_role"]),
                "archetype": str(item["role"]["archetype"]),
                "model": str(item.get("resolved_model") or ""),
                "status": str(item["handoff"]["status"]),
                "parallel_group": str(item["step"].get("parallel_group") or ""),
            }
            for item in step_results
        ],
        "step_handoffs": [item["handoff"] for item in step_results],
        "score": {
            "composite": composite,
            "delta": delta,
            "passed": gatekeeper_output.get("passed"),
        },
        "gatekeeper_verdict": _iteration_gatekeeper_verdict(gatekeeper_output),
        "stagnation": {
            "mode": str(stagnation.get("stagnation_mode", "none")),
            "evidence_progress_mode": str(stagnation.get("evidence_progress_mode", "none") or "none"),
            "recent_composites": structured_score_values(stagnation.get("recent_composites")),
            "recent_deltas": structured_score_values(stagnation.get("recent_deltas")),
            "consecutive_low_delta": _int_value(stagnation.get("consecutive_low_delta")),
            "coverage_status": str(stagnation.get("latest_coverage_status") or "pending"),
            "covered_check_count": _int_value(stagnation.get("latest_covered_check_count")),
            "missing_check_count": _int_value(stagnation.get("latest_missing_check_count")),
            "covered_check_ids": _string_list(stagnation.get("latest_covered_check_ids")),
            "missing_check_ids": _string_list(stagnation.get("latest_missing_check_ids")),
            "coverage_top_gaps": _normalize_coverage_gap_rows(stagnation.get("latest_coverage_top_gaps")),
            "consecutive_no_required_coverage_delta": _int_value(stagnation.get("consecutive_no_required_coverage_delta")),
        },
        "latest_refs": {
            "summary_path": layout.relative(layout.iteration_summary_path(iter_id)),
            "latest_gatekeeper": (
                layout.relative(
                    layout.step_handoff_path(
                        iter_id,
                        gatekeeper_handoff["source"]["step_order"],
                        gatekeeper_handoff["source"]["step_id"],
                    )
                )
                if gatekeeper_handoff
                else None
            ),
            "latest_by_step": latest_by_step,
            "latest_by_role": latest_by_role,
            "latest_by_archetype": latest_by_archetype,
        },
    }


def derive_latest_state(previous_state: dict, iteration_summary: dict) -> dict:
    latest_by_step = dict(previous_state.get("latest_by_step") or {})
    latest_by_step.update(iteration_summary["latest_refs"]["latest_by_step"])
    latest_by_role = dict(previous_state.get("latest_by_role") or {})
    latest_by_role.update(iteration_summary["latest_refs"]["latest_by_role"])
    latest_by_archetype = dict(previous_state.get("latest_by_archetype") or {})
    latest_by_archetype.update(iteration_summary["latest_refs"]["latest_by_archetype"])
    latest_gatekeeper = iteration_summary["latest_refs"].get("latest_gatekeeper")
    if latest_gatekeeper is None:
        latest_gatekeeper = previous_state.get("latest_gatekeeper")
    return {
        "latest_iteration": iteration_summary["iter"],
        "latest_by_step": latest_by_step,
        "latest_by_role": latest_by_role,
        "latest_by_archetype": latest_by_archetype,
        "latest_gatekeeper": latest_gatekeeper,
        "latest_summary_path": iteration_summary["latest_refs"]["summary_path"],
    }


def _iteration_gatekeeper_verdict(output: dict) -> dict:
    if not isinstance(output, dict) or not output:
        return {
            "passed": None,
            "decision_summary": "",
            "blocking_issues": [],
            "feedback_to_builder": "",
            "evidence_refs": [],
            "evidence_claims": [],
            "residual_risks": [],
            "coverage_results": [],
        }
    return {
        "passed": structured_bool_is_true(output.get("passed")),
        "decision_summary": _clean_text(output.get("decision_summary")),
        "blocking_issues": _gatekeeper_blockers(output),
        "feedback_to_builder": _clean_text(output.get("feedback_to_builder") or output.get("feedback_to_generator")),
        "evidence_refs": _string_list(output.get("evidence_refs"))[:20],
        "evidence_claims": _string_list(output.get("evidence_claims"))[:20],
        "residual_risks": _string_list(output.get("residual_risks"))[:20],
        "coverage_results": _evidence_coverage_results(output.get("coverage_results")),
    }


def _int_value(value: object) -> int:
    return structured_non_negative_int(value)


def _number_value(value: object) -> float | None:
    return structured_score_value(value)
