from __future__ import annotations

"""Markdown summary projection for a runner iteration."""

from collections.abc import Callable
from typing import Protocol

from loopora.service_iteration_result_enrichment import empty_status_counts, verifier_passed
from loopora.utils import structured_optional_finite_number

TruncateText = Callable[..., str]


class IterationSummaryReport(Protocol):
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


class IterationSummaryRequestLike(Protocol):
    run: dict
    compiled_spec: dict
    report: IterationSummaryReport
    exhausted: bool


def format_inline_code_list(items: list[str], *, empty: str = "none", limit: int = 5) -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        return empty
    visible = [f"`{item}`" for item in values[:limit]]
    if len(values) > limit:
        visible.append(f"`+{len(values) - limit} more`")
    return ", ".join(visible)


def format_failure_refs(items: list[dict], *, limit: int = 4) -> str:
    if not items:
        return "none"
    visible = []
    for item in items[:limit]:
        label = item.get("title") or item.get("id") or "unknown"
        source = item.get("source")
        if source == "dynamic":
            label = f"{label} [dynamic]"
        visible.append(f"`{label}`")
    if len(items) > limit:
        visible.append(f"`+{len(items) - limit} more`")
    return ", ".join(visible)


def format_metric_refs(metrics: list[dict], *, limit: int = 4) -> str:
    if not metrics:
        return "none"
    visible = []
    for metric in metrics[:limit]:
        name = str(metric.get("name", "")).strip() or "unknown_metric"
        value = metric.get("value")
        threshold = metric.get("threshold")
        if value is None or threshold is None:
            visible.append(f"`{name}`")
        else:
            visible.append(f"`{name}={value}` (threshold `{threshold}`)")
    if len(metrics) > limit:
        visible.append(f"`+{len(metrics) - limit} more`")
    return ", ".join(visible)


def build_iteration_summary_markdown(request: IterationSummaryRequestLike, *, truncate_text: TruncateText) -> str:
    report = request.report
    verifier_result = report.verifier_result
    completion_mode = str(request.run.get("completion_mode", "gatekeeper")).strip().lower() or "gatekeeper"
    verifier_passed_value = verifier_passed(verifier_result)
    lines = [
        *_summary_header_lines(
            request,
            completion_mode=completion_mode,
            verifier_passed_value=verifier_passed_value,
        ),
        "",
        _status_line(request, completion_mode=completion_mode, verifier_passed_value=verifier_passed_value),
        "",
        *_generator_lines(report.generator_result, truncate_text=truncate_text),
        "",
        *_tester_lines(report.tester_result, truncate_text=truncate_text),
        "",
        *_verifier_lines(verifier_result, truncate_text=truncate_text),
    ]
    if report.challenger_result is not None:
        lines.extend(["", *_challenger_lines(report.challenger_result, truncate_text=truncate_text)])
    lines.extend(["", *_artifact_lines()])
    return "\n".join(lines).rstrip() + "\n"


def _status_line(
    request: IterationSummaryRequestLike,
    *,
    completion_mode: str,
    verifier_passed_value: bool,
) -> str:
    if request.exhausted and completion_mode == "rounds":
        return "Planned rounds completed."
    if request.exhausted:
        return "Max iterations exhausted."
    if verifier_passed_value and completion_mode == "gatekeeper":
        return "All checks passed in this iteration."
    if verifier_passed_value:
        return "Verifier passed in this iteration, but the run stays in round-based mode."
    return "Still iterating."


def _summary_header_lines(
    request: IterationSummaryRequestLike,
    *,
    completion_mode: str,
    verifier_passed_value: bool,
) -> list[str]:
    run = request.run
    compiled_spec = request.compiled_spec
    report = request.report
    verifier_result = report.verifier_result
    failed = verifier_result.get("failed_check_titles", verifier_result.get("failed_check_ids", []))
    check_mode = compiled_spec.get("check_mode", "specified")
    return [
        "# Loopora Run Summary",
        "",
        f"- Workdir: `{run['workdir']}`",
        f"- Iteration: `{report.iter_id + 1}`",
        f"- Check mode: `{check_mode}`",
        f"- Check count: `{len(compiled_spec.get('checks', []))}`",
        f"- Completion mode: `{completion_mode}`",
        f"- Iteration interval seconds: `{run.get('iteration_interval_seconds', 0.0)}`",
        f"- Composite score: `{verifier_result['composite_score']}`",
        f"- Score delta vs previous iteration: {_score_delta_text(verifier_result, report.previous_composite)}",
        f"- Passed: `{verifier_passed_value}`",
        f"- Stagnation mode: `{report.stagnation.get('stagnation_mode', 'none')}`",
        f"- Failed checks: {format_inline_code_list(failed, empty='none', limit=4)}",
        "- Role modes: "
        f"generator=`{report.generator_mode}`, tester=`{report.tester_mode}`, verifier=`{report.verifier_mode}`",
    ]


def _score_delta_text(verifier_result: dict, previous_composite: float | None) -> str:
    composite_score = structured_optional_finite_number(verifier_result.get("composite_score"))
    previous_score = structured_optional_finite_number(previous_composite)
    if composite_score is None or previous_score is None:
        return "`n/a`"
    return f"`{round(composite_score - previous_score, 6):+}`"


def _generator_lines(generator_result: dict, *, truncate_text: TruncateText) -> list[str]:
    return [
        "## Generator",
        f"- Attempted: {truncate_text(generator_result.get('attempted') or generator_result.get('summary'), 280) or 'none'}",
        f"- Changed files: {format_inline_code_list(list(generator_result.get('changed_files', [])))}",
        f"- Assumption: {truncate_text(generator_result.get('assumption'), 220) or 'none'}",
        f"- Abandoned: {truncate_text(generator_result.get('abandoned'), 220) or 'none'}",
    ]


def _tester_lines(tester_result: dict, *, truncate_text: TruncateText) -> list[str]:
    overall_counts = tester_result.get("status_counts", {}).get("overall", empty_status_counts())
    dynamic_counts = tester_result.get("status_counts", {}).get("dynamic_checks", empty_status_counts())
    return [
        "## Tester",
        "- Overall statuses: "
        f"passed=`{overall_counts['passed']}`, failed=`{overall_counts['failed']}`, "
        f"errored=`{overall_counts['errored']}`, skipped=`{overall_counts['skipped']}`",
        "- Dynamic checks: "
        f"passed=`{dynamic_counts['passed']}`, failed=`{dynamic_counts['failed']}`, "
        f"errored=`{dynamic_counts['errored']}`, skipped=`{dynamic_counts['skipped']}`",
        f"- Non-passing items: {format_failure_refs(list(tester_result.get('failed_items', [])))}",
        f"- Observations: {truncate_text(tester_result.get('tester_observations'), 320) or 'none'}",
    ]


def _verifier_lines(verifier_result: dict, *, truncate_text: TruncateText) -> list[str]:
    return [
        "## Verifier",
        f"- Decision: {truncate_text(verifier_result.get('decision_summary'), 320) or 'none'}",
        f"- Failing metrics: {format_metric_refs(list(verifier_result.get('failing_metrics', [])))}",
        "- Hard constraint violations: "
        f"{format_inline_code_list(list(verifier_result.get('hard_constraint_violations', [])), empty='none', limit=3)}",
        "- Priority failures: "
        f"{format_inline_code_list([item.get('error_code', 'unknown') for item in verifier_result.get('priority_failures', [])], empty='none', limit=4)}",
        f"- Next actions: {format_inline_code_list(list(verifier_result.get('next_actions', [])), empty='none', limit=3)}",
    ]


def _challenger_lines(challenger_result: dict, *, truncate_text: TruncateText) -> list[str]:
    return [
        "## Challenger",
        f"- Mode: `{challenger_result.get('mode', 'unknown')}`",
        f"- Recommended shift: {truncate_text(challenger_result.get('analysis', {}).get('recommended_shift'), 220) or 'none'}",
        f"- Seed question: {truncate_text(challenger_result.get('seed_question'), 220) or 'none'}",
    ]


def _artifact_lines() -> list[str]:
    return [
        "## Artifacts",
        "- Inspect `tester_output.json`, `verifier_verdict.json`, `iteration_log.jsonl`, and `events.jsonl` for full details.",
    ]
