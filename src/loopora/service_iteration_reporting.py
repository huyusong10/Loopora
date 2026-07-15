from __future__ import annotations

from dataclasses import dataclass

from loopora.service_iteration_result_enrichment import (
    build_decision_summary,
    collect_non_passing_items,
    count_statuses,
    empty_status_counts,
    enrich_tester_result,
    enrich_verifier_result,
    split_action_hints,
    verifier_passed,
)
from loopora.service_iteration_summary_markdown import (
    build_iteration_summary_markdown,
    format_failure_refs,
    format_inline_code_list,
    format_metric_refs,
)

"""Structured iteration log entry projection."""

from typing import Protocol

from loopora.score_history_values import structured_score_values


from loopora.utils import structured_non_negative_int, structured_optional_finite_number

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


@dataclass(frozen=True)
class IterationReportContext:
    iter_id: int
    generator_result: dict
    tester_result: dict
    verifier_result: dict
    stagnation: dict
    generator_mode: str
    tester_mode: str
    verifier_mode: str
    previous_composite: float | None
    challenger_result: dict | None = None


@dataclass(frozen=True)
class IterationSummaryRequest:
    run: dict
    compiled_spec: dict
    report: IterationReportContext
    exhausted: bool = False


class ServiceIterationReportingMixin:
    @staticmethod
    def _verifier_passed(verifier_result: dict) -> bool:
        return verifier_passed(verifier_result)

    @staticmethod
    def _empty_status_counts() -> dict[str, int]:
        return empty_status_counts()

    def _count_statuses(self, items: list[dict]) -> dict[str, int]:
        return count_statuses(items)

    def _collect_non_passing_items(self, items: list[dict], *, source: str) -> list[dict]:
        return collect_non_passing_items(items, source=source, truncate_text=self._truncate_text)

    def _enrich_tester_result(self, tester_result: dict) -> dict:
        return enrich_tester_result(tester_result, truncate_text=self._truncate_text)

    def _build_decision_summary(self, verifier_result: dict, tester_result: dict) -> str:
        return build_decision_summary(verifier_result, tester_result, truncate_text=self._truncate_text)

    @staticmethod
    def _split_action_hints(feedback: str | None) -> list[str]:
        return split_action_hints(feedback)

    def _enrich_verifier_result(self, verifier_result: dict, compiled_spec: dict, tester_result: dict) -> dict:
        return enrich_verifier_result(
            verifier_result,
            compiled_spec,
            tester_result,
            truncate_text=self._truncate_text,
        )

    def _format_inline_code_list(self, items: list[str], *, empty: str = "none", limit: int = 5) -> str:
        return format_inline_code_list(items, empty=empty, limit=limit)

    def _format_failure_refs(self, items: list[dict], *, limit: int = 4) -> str:
        return format_failure_refs(items, limit=limit)

    def _format_metric_refs(self, metrics: list[dict], *, limit: int = 4) -> str:
        return format_metric_refs(metrics, limit=limit)

    def _build_generator_log_entry(self, iter_id: int, generator_result: dict, mode: str) -> dict:
        return build_generator_log_entry(iter_id, generator_result, mode)

    def _build_iteration_log_entry(self, report: IterationReportContext) -> dict:
        return build_iteration_log_entry(report)

    def _build_summary(self, request: IterationSummaryRequest) -> str:
        return build_iteration_summary_markdown(request, truncate_text=self._truncate_text)
