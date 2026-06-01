from __future__ import annotations

from dataclasses import dataclass

from loopora.service_iteration_log_entries import build_generator_log_entry, build_iteration_log_entry
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
