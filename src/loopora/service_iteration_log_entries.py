from __future__ import annotations

"""Structured iteration log entry projection."""

from typing import Protocol

from loopora.score_history_values import structured_score_values
from loopora.service_iteration_result_enrichment import verifier_passed
from loopora.structured_numbers import structured_non_negative_int, structured_optional_finite_number
from loopora.utils import utc_now


class IterationLogReport(Protocol):
    iter_id: int
    generator_result: dict
    tester_result: dict
    verifier_result: dict
    stagnation: dict
    generator_mode: str
    tester_mode: str
    verifier_mode: str
    previous_composite: float | None
    challenger_result: dict | None


def build_generator_log_entry(iter_id: int, generator_result: dict, mode: str) -> dict:
    return {
        "phase": "generator",
        "iter": iter_id,
        "timestamp": utc_now(),
        "mode": mode,
        "attempted": generator_result.get("attempted", ""),
        "summary": generator_result.get("summary", ""),
        "assumption": generator_result.get("assumption", ""),
        "abandoned": generator_result.get("abandoned", ""),
        "changed_files": list(generator_result.get("changed_files", [])),
    }


def build_iteration_log_entry(report: IterationLogReport) -> dict:
    composite_score = structured_optional_finite_number(report.verifier_result.get("composite_score"))
    previous_score = structured_optional_finite_number(report.previous_composite)
    entry = {
        "phase": "complete",
        "iter": report.iter_id,
        "timestamp": utc_now(),
        "modes": {
            "generator": report.generator_mode,
            "tester": report.tester_mode,
            "verifier": report.verifier_mode,
        },
        "score": {
            "composite": composite_score,
            "delta": round(composite_score - previous_score, 6) if composite_score is not None and previous_score is not None else None,
            "passed": verifier_passed(report.verifier_result),
        },
        "generator": {
            "attempted": report.generator_result.get("attempted", ""),
            "summary": report.generator_result.get("summary", ""),
            "assumption": report.generator_result.get("assumption", ""),
            "abandoned": report.generator_result.get("abandoned", ""),
            "changed_files": list(report.generator_result.get("changed_files", [])),
        },
        "tester": {
            "execution_summary": dict(report.tester_result.get("execution_summary", {})),
            "status_counts": dict(report.tester_result.get("status_counts", {})),
            "failed_items": list(report.tester_result.get("failed_items", [])),
            "tester_observations": report.tester_result.get("tester_observations", ""),
        },
        "verifier": {
            "passed": verifier_passed(report.verifier_result),
            "decision_summary": report.verifier_result.get("decision_summary", ""),
            "failed_check_ids": list(report.verifier_result.get("failed_check_ids", [])),
            "failed_check_titles": list(report.verifier_result.get("failed_check_titles", [])),
            "failing_metrics": list(report.verifier_result.get("failing_metrics", [])),
            "hard_constraint_violations": list(report.verifier_result.get("hard_constraint_violations", [])),
            "priority_failures": list(report.verifier_result.get("priority_failures", [])),
            "feedback_to_generator": report.verifier_result.get("feedback_to_generator", ""),
            "next_actions": list(report.verifier_result.get("next_actions", [])),
            "evidence_refs": list(report.verifier_result.get("evidence_refs", [])),
            "evidence_gate_status": report.verifier_result.get("evidence_gate_status", ""),
        },
        "stagnation": {
            "mode": report.stagnation.get("stagnation_mode", "none"),
            "recent_composites": structured_score_values(report.stagnation.get("recent_composites")),
            "recent_deltas": structured_score_values(report.stagnation.get("recent_deltas")),
            "consecutive_low_delta": structured_non_negative_int(report.stagnation.get("consecutive_low_delta")),
        },
    }
    if report.challenger_result is not None:
        entry["challenger"] = {
            "mode": report.challenger_result.get("mode"),
            "analysis": dict(report.challenger_result.get("analysis", {})),
            "seed_question": report.challenger_result.get("seed_question", ""),
            "meta_note": report.challenger_result.get("meta_note", ""),
        }
    return entry
