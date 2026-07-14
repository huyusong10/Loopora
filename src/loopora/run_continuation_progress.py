from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from loopora.loop_run_progress import build_loop_run_progress

CONTINUATION_ACTION_MODES = frozenset(
    {
        "advisory_follow_up",
        "change_approach",
        "close_gaps",
        "continue_progress",
        "repair_regression",
        "retry_lifecycle",
        "review_contract_change",
        "stabilize_mixed",
    }
)

_PROGRESS_ACTION_MODES = {
    "progressed": "continue_progress",
    "mixed": "stabilize_mixed",
    "regressed": "repair_regression",
    "no_progress": "change_approach",
    "contract_changed": "review_contract_change",
}

_ACTION_POLICIES = {
    "advisory_follow_up": "Work only on the bounded advisory targets without reopening the recorded task result.",
    "change_approach": "Do not repeat the previous approach as-is. Explain why it produced no target-level progress, then change strategy or return to plan review if the contract is the blocker.",
    "close_gaps": "Use the frozen unresolved targets as the next evidence scope; no cross-run progress claim is available yet.",
    "continue_progress": "Preserve the targets that improved, avoid redoing already covered work, and focus the remaining gaps.",
    "repair_regression": "Restore regressed target evidence before broadening scope, and do not hide the regression behind new evidence volume.",
    "retry_lifecycle": "Restore the failed execution boundary without treating the failed lifecycle as task evidence.",
    "review_contract_change": "Do not compare progress across the changed target contract. Confirm the current judgment boundary before continuing evidence work.",
    "stabilize_mixed": "Protect the targets that improved and repair every regression before broadening the task.",
}


def build_continuation_progress_context(
    runs: Sequence[Mapping[str, Any]],
    *,
    source_run_id: str,
    current_run_id: str = "",
) -> dict[str, Any]:
    source_id = str(source_run_id or "").strip()
    current_id = str(current_run_id or "").strip()
    history = [
        dict(run)
        for run in runs
        if isinstance(run, Mapping) and str(run.get("id") or "").strip() != current_id
    ]
    source_index = next(
        (index for index, run in enumerate(history) if str(run.get("id") or "").strip() == source_id),
        None,
    )
    if source_index is None:
        return _empty_progress_context(source_id, reason="source_run_unavailable")
    if source_index != 0:
        return _empty_progress_context(source_id, reason="source_run_not_latest")
    progress = build_loop_run_progress(history[:2])
    return {
        "schema_version": 1,
        "status": str(progress.get("status") or "unavailable"),
        "reason": str(progress.get("reason") or ""),
        "comparable": progress.get("comparable") is True,
        "source_run_id": source_id,
        "prior_run_id": str(progress.get("previous_run_id") or ""),
        "improved_target_count": _non_negative_int(progress.get("improved_target_count")),
        "regressed_target_count": _non_negative_int(progress.get("regressed_target_count")),
        "closed_gap_count": _non_negative_int(progress.get("closed_gap_count")),
        "reopened_target_count": _non_negative_int(progress.get("reopened_target_count")),
        "current_gap_count": _non_negative_int(progress.get("current_gap_count")),
        "current_required_gap_count": _non_negative_int(progress.get("current_required_gap_count")),
        "added_target_count": _non_negative_int(progress.get("added_target_count")),
        "removed_target_count": _non_negative_int(progress.get("removed_target_count")),
        "changed_target_count": _non_negative_int(progress.get("changed_target_count")),
        "improved_targets": _target_rows(progress.get("improved_targets")),
        "regressed_targets": _target_rows(progress.get("regressed_targets")),
        "changed_target_ids": _string_items(progress.get("changed_target_ids")),
    }


def continuation_action_mode(*, reason: str, progress_status: str) -> str:
    normalized_reason = str(reason or "").strip()
    if normalized_reason == "recorded_advisory_follow_up":
        return "advisory_follow_up"
    if normalized_reason == "previous_lifecycle_failure_retry":
        return "retry_lifecycle"
    return _PROGRESS_ACTION_MODES.get(str(progress_status or "").strip(), "close_gaps")


def continuation_action_policy(action_mode: str) -> str:
    return _ACTION_POLICIES.get(str(action_mode or "").strip(), _ACTION_POLICIES["close_gaps"])


def normalize_continuation_progress_context(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        "schema_version": 1,
        "status": str(value.get("status") or "unavailable").strip() or "unavailable",
        "reason": str(value.get("reason") or "").strip(),
        "comparable": value.get("comparable") is True,
        "source_run_id": str(value.get("source_run_id") or "").strip(),
        "prior_run_id": str(value.get("prior_run_id") or "").strip(),
        "improved_target_count": _non_negative_int(value.get("improved_target_count")),
        "regressed_target_count": _non_negative_int(value.get("regressed_target_count")),
        "closed_gap_count": _non_negative_int(value.get("closed_gap_count")),
        "reopened_target_count": _non_negative_int(value.get("reopened_target_count")),
        "current_gap_count": _non_negative_int(value.get("current_gap_count")),
        "current_required_gap_count": _non_negative_int(value.get("current_required_gap_count")),
        "added_target_count": _non_negative_int(value.get("added_target_count")),
        "removed_target_count": _non_negative_int(value.get("removed_target_count")),
        "changed_target_count": _non_negative_int(value.get("changed_target_count")),
        "improved_targets": _target_rows(value.get("improved_targets")),
        "regressed_targets": _target_rows(value.get("regressed_targets")),
        "changed_target_ids": _string_items(value.get("changed_target_ids")),
    }


def _empty_progress_context(source_run_id: str, *, reason: str) -> dict[str, Any]:
    return normalize_continuation_progress_context(
        {
            "status": "unavailable",
            "reason": reason,
            "source_run_id": source_run_id,
        }
    )


def _target_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [
        {
            "target_id": str(item.get("target_id") or "").strip(),
            "text": str(item.get("text") or "").strip(),
            "required": item.get("required") is True,
            "previous_status": str(item.get("previous_status") or "missing").strip() or "missing",
            "current_status": str(item.get("current_status") or "missing").strip() or "missing",
            "change": str(item.get("change") or "unchanged").strip() or "unchanged",
        }
        for item in value
        if isinstance(item, Mapping) and str(item.get("target_id") or "").strip()
    ][:5]


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:8]


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0
