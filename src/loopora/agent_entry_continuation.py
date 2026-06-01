from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_task_proof import PASSING_TASK_VERDICT_STATUSES
from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection
from loopora.run_projection_fields import task_verdict_from_run
from loopora.service_types import TERMINAL_RUN_STATUSES
from loopora.structured_numbers import coerced_non_negative_int as non_negative_int
from loopora.task_verdicts import normalize_task_verdict
from loopora.utils import read_json


def agent_entry_continuation_summary(continuation: dict[str, Any]) -> dict[str, Any]:
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    verdict = continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    buckets = verdict.get("buckets") if isinstance(verdict.get("buckets"), dict) else {}
    return {
        "reason": str(continuation.get("reason") or "").strip(),
        "previous_run_id": str(continuation.get("previous_run_id") or "").strip(),
        "previous_run_status": str(continuation.get("previous_run_status") or "").strip(),
        "previous_task_verdict": verdict,
        "coverage": {
            "status": str(coverage.get("status") or "").strip(),
            "covered_check_count": non_negative_int(coverage.get("covered_check_count")),
            "missing_check_count": non_negative_int(coverage.get("missing_check_count")),
            "target_count": non_negative_int(coverage.get("target_count")),
            "covered_target_count": non_negative_int(coverage.get("covered_target_count")),
            "weak_target_count": non_negative_int(coverage.get("weak_target_count")),
            "missing_target_count": non_negative_int(coverage.get("missing_target_count")),
            "blocked_target_count": non_negative_int(coverage.get("blocked_target_count")),
            "missing_check_ids": string_list(coverage.get("missing_check_ids"), limit=8),
            "top_gaps": list_of_dicts(coverage.get("top_gaps"), limit=4),
        },
        "next_focus": string_list(continuation.get("next_focus"), limit=5),
        "focus_blocking": string_list(
            [bucket_focus_text(item) for item in list_of_dicts(buckets.get("blocking"), limit=4)],
            limit=4,
        ),
        "focus_unproven": string_list(
            [bucket_focus_text(item) for item in list_of_dicts(buckets.get("unproven"), limit=4)],
            limit=4,
        ),
        "focus_weak": string_list(
            [bucket_focus_text(item) for item in list_of_dicts(buckets.get("weak"), limit=4)],
            limit=4,
        ),
        "previous_task_verdict_path": str(continuation.get("previous_task_verdict_path") or "").strip(),
        "previous_evidence_coverage_path": str(continuation.get("previous_evidence_coverage_path") or "").strip(),
    }


def agent_native_continuation_context_for_terminal_run(previous_run: dict[str, Any], previous_layout: Any) -> dict[str, Any]:
    task_verdict = task_verdict_context_for_run(previous_run, previous_layout)
    coverage = coverage_context_for_run(previous_layout)
    return {
        "active": True,
        "reason": "terminal_task_verdict_requires_next_run",
        "previous_run_id": str(previous_run.get("id") or "").strip(),
        "previous_run_path": f"/runs/{previous_run.get('id')}",
        "previous_run_status": str(previous_run.get("status") or "").strip(),
        "previous_task_verdict": task_verdict,
        "previous_task_verdict_path": str(previous_layout.task_verdict_path.resolve())
        if previous_layout.task_verdict_path.exists()
        else "",
        "previous_evidence_coverage_path": str(previous_layout.evidence_coverage_path.resolve())
        if previous_layout.evidence_coverage_path.exists()
        else "",
        "coverage": coverage,
        "next_focus": agent_native_continuation_focus(task_verdict, coverage),
    }


def task_verdict_context_for_run(run: dict[str, Any], layout: Any) -> dict[str, Any]:
    task_verdict = normalize_task_verdict(task_verdict_from_run(run))
    if not task_verdict and layout.task_verdict_path.exists():
        task_verdict = normalize_task_verdict(read_json_object(layout.task_verdict_path))
    buckets = task_verdict.get("buckets") if isinstance(task_verdict.get("buckets"), dict) else {}
    return {
        "status": str(task_verdict.get("status") or "").strip(),
        "source": str(task_verdict.get("source") or "").strip(),
        "summary": str(task_verdict.get("summary") or "").strip(),
        "buckets": {
            "proven": list_of_dicts(buckets.get("proven")),
            "weak": list_of_dicts(buckets.get("weak")),
            "unproven": list_of_dicts(buckets.get("unproven")),
            "blocking": list_of_dicts(buckets.get("blocking")),
            "residual_risk": list_of_dicts(buckets.get("residual_risk")),
        },
    }


def coverage_context_for_run(layout: Any) -> dict[str, Any]:
    coverage_projection = read_json_object(layout.evidence_coverage_path)
    coverage_summary = summarize_evidence_coverage_projection(
        coverage_projection,
        coverage_path_available=layout.evidence_coverage_path.exists(),
    )
    return {
        "status": str(coverage_summary.get("status") or "pending"),
        "covered_check_count": non_negative_int(coverage_summary.get("covered_check_count")),
        "missing_check_count": non_negative_int(coverage_summary.get("missing_check_count")),
        "target_count": non_negative_int(coverage_summary.get("target_count")),
        "covered_target_count": non_negative_int(coverage_summary.get("covered_target_count")),
        "weak_target_count": non_negative_int(coverage_summary.get("weak_target_count")),
        "missing_target_count": non_negative_int(coverage_summary.get("missing_target_count")),
        "blocked_target_count": non_negative_int(coverage_summary.get("blocked_target_count")),
        "covered_check_ids": string_list(coverage_summary.get("covered_check_ids"), limit=20),
        "missing_check_ids": string_list(coverage_summary.get("missing_check_ids"), limit=20),
        "top_gaps": list_of_dicts(coverage_summary.get("top_gaps"), limit=5),
    }


def agent_native_continuation_focus(task_verdict: dict[str, Any], coverage: dict[str, Any]) -> list[str]:
    focus: list[str] = []
    summary = str(task_verdict.get("summary") or "").strip()
    if summary:
        focus.append(summary)
    buckets = task_verdict.get("buckets") if isinstance(task_verdict.get("buckets"), dict) else {}
    for bucket_name in ("blocking", "unproven", "weak"):
        for item in list_of_dicts(buckets.get(bucket_name), limit=4):
            text = bucket_focus_text(item)
            if text:
                focus.append(text)
    for gap in list_of_dicts(coverage.get("top_gaps"), limit=5):
        target_id = str(gap.get("target_id") or "").strip()
        text = str(gap.get("text") or gap.get("reason") or "").strip()
        if target_id or text:
            focus.append(f"{target_id}: {text}".strip(": "))
    return dedupe_strings(focus, limit=8)


def task_verdict_status_for_run(run: dict[str, Any]) -> str:
    return str(task_verdict_from_run(run).get("status") or "").strip()


def terminal_agent_run_needs_next_pass(run: dict[str, Any]) -> bool:
    if str(run.get("status") or "").strip() not in TERMINAL_RUN_STATUSES:
        return False
    return task_verdict_status_for_run(run) not in PASSING_TASK_VERDICT_STATUSES


def bucket_focus_text(item: dict[str, Any]) -> str:
    return str(
        item.get("summary")
        or item.get("text")
        or item.get("label")
        or item.get("reason")
        or item.get("id")
        or ""
    ).strip()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def string_list(value: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] if limit is not None else items


def list_of_dicts(value: object, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items = [dict(item) for item in value if isinstance(item, dict)]
    return items[:limit] if limit is not None else items


def dedupe_strings(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
        if len(deduped) >= limit:
            break
    return deduped
