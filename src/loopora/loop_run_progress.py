from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout
from loopora.run_projection_fields import task_verdict_from_run
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.service_types import TERMINAL_RUN_STATUSES

RUN_PROGRESS_STATUSES = frozenset(
    {
        "baseline",
        "active",
        "progressed",
        "mixed",
        "regressed",
        "no_progress",
        "contract_changed",
        "unavailable",
    }
)
_COVERAGE_STATUS_RANK = {"blocked": -1, "missing": 0, "weak": 1, "covered": 2}


def build_loop_run_progress(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized_runs = [dict(run) for run in runs if isinstance(run, Mapping)]
    latest = normalized_runs[0] if normalized_runs else {}
    previous = normalized_runs[1] if len(normalized_runs) > 1 else {}
    payload = _base_progress_payload(normalized_runs, latest, previous)
    initial_state = _precomparison_state(latest, previous)
    if initial_state is not None:
        status, reason = initial_state
        return {**payload, "status": status, "reason": reason}

    latest_coverage = _coverage_projection(latest)
    previous_coverage = _coverage_projection(previous)
    latest_targets = _target_map(latest_coverage)
    previous_targets = _target_map(previous_coverage)
    if not latest_targets or not previous_targets:
        return {**payload, "status": "unavailable", "reason": "coverage_targets_unavailable"}

    shared_ids = sorted(latest_targets.keys() & previous_targets.keys())
    added_ids = sorted(latest_targets.keys() - previous_targets.keys())
    removed_ids = sorted(previous_targets.keys() - latest_targets.keys())
    changed_ids = [
        target_id
        for target_id in shared_ids
        if _target_contract_signature(latest_targets[target_id]) != _target_contract_signature(previous_targets[target_id])
    ]
    comparisons = [
        _target_comparison(target_id, previous_targets[target_id], latest_targets[target_id])
        for target_id in shared_ids
        if target_id not in changed_ids
    ]
    improved = [item for item in comparisons if item["change"] == "improved"]
    regressed = [item for item in comparisons if item["change"] == "regressed"]
    contract_changed = bool(added_ids or removed_ids or changed_ids)
    status = _comparison_status(improved, regressed, contract_changed=contract_changed)
    return {
        **payload,
        "status": status,
        "reason": "coverage_target_comparison",
        "comparable": not contract_changed,
        "shared_target_count": len(shared_ids),
        "added_target_count": len(added_ids),
        "removed_target_count": len(removed_ids),
        "changed_target_count": len(changed_ids),
        "added_target_ids": added_ids,
        "removed_target_ids": removed_ids,
        "changed_target_ids": changed_ids,
        "improved_target_count": len(improved),
        "regressed_target_count": len(regressed),
        "unchanged_target_count": len(comparisons) - len(improved) - len(regressed),
        "closed_gap_count": sum(item["current_status"] == "covered" for item in improved),
        "reopened_target_count": sum(item["previous_status"] == "covered" for item in regressed),
        "current_gap_count": sum(_target_status(target) != "covered" for target in latest_targets.values()),
        "current_required_gap_count": sum(
            _target_status(target) != "covered" and coverage_target_is_required(target)
            for target in latest_targets.values()
        ),
        "improved_targets": improved[:5],
        "regressed_targets": regressed[:5],
        "latest_coverage_status": str(latest_coverage.get("status") or "pending"),
        "previous_coverage_status": str(previous_coverage.get("status") or "pending"),
        "latest_evidence_count": _non_negative_int(latest_coverage.get("evidence_count")),
        "previous_evidence_count": _non_negative_int(previous_coverage.get("evidence_count")),
        "evidence_count_delta": _non_negative_int(latest_coverage.get("evidence_count"))
        - _non_negative_int(previous_coverage.get("evidence_count")),
    }


def _precomparison_state(latest: dict, previous: dict) -> tuple[str, str] | None:
    state: tuple[str, str] | None = None
    if not latest:
        state = ("unavailable", "no_runs")
    elif not previous:
        state = ("baseline", "first_run")
    elif str(latest.get("status") or "").strip() not in TERMINAL_RUN_STATUSES:
        state = ("active", "latest_run_active")
    elif run_result_is_lifecycle_failure(latest):
        state = ("unavailable", "latest_lifecycle_failure")
    elif str(previous.get("status") or "").strip() not in TERMINAL_RUN_STATUSES:
        state = ("unavailable", "previous_run_not_terminal")
    elif run_result_is_lifecycle_failure(previous):
        state = ("unavailable", "previous_lifecycle_failure")
    return state


def _base_progress_payload(runs: list[dict], latest: dict, previous: dict) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "unavailable",
        "reason": "",
        "comparable": False,
        "run_count": len(runs),
        "latest_run_id": str(latest.get("id") or ""),
        "previous_run_id": str(previous.get("id") or ""),
        "latest_run_status": str(latest.get("status") or ""),
        "previous_run_status": str(previous.get("status") or ""),
        "latest_task_verdict_status": _task_verdict_status(latest),
        "previous_task_verdict_status": _task_verdict_status(previous),
        "shared_target_count": 0,
        "added_target_count": 0,
        "removed_target_count": 0,
        "changed_target_count": 0,
        "added_target_ids": [],
        "removed_target_ids": [],
        "changed_target_ids": [],
        "improved_target_count": 0,
        "regressed_target_count": 0,
        "unchanged_target_count": 0,
        "closed_gap_count": 0,
        "reopened_target_count": 0,
        "current_gap_count": 0,
        "current_required_gap_count": 0,
        "improved_targets": [],
        "regressed_targets": [],
        "latest_coverage_status": "",
        "previous_coverage_status": "",
        "latest_evidence_count": 0,
        "previous_evidence_count": 0,
        "evidence_count_delta": 0,
    }


def _coverage_projection(run: Mapping[str, Any]) -> dict[str, Any]:
    runs_dir = str(run.get("runs_dir") or "").strip()
    if not runs_dir:
        return {}
    try:
        projection = load_or_build_evidence_coverage_projection(RunArtifactLayout(Path(runs_dir)))
    except (OSError, UnicodeError, ValueError):
        return {}
    return dict(projection) if isinstance(projection, Mapping) else {}


def _target_map(coverage: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    for raw_target in list(coverage.get("targets") or []):
        if not isinstance(raw_target, Mapping):
            continue
        target_id = str(raw_target.get("id") or raw_target.get("target_id") or "").strip()
        if target_id and target_id not in targets:
            targets[target_id] = dict(raw_target)
    return targets


def _target_contract_signature(target: Mapping[str, Any]) -> tuple[bool, str, str]:
    return (
        coverage_target_is_required(target),
        str(target.get("kind") or "").strip(),
        str(target.get("text") or target.get("label") or "").strip(),
    )


def _target_comparison(target_id: str, previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    previous_status = _target_status(previous)
    current_status = _target_status(current)
    previous_rank = _COVERAGE_STATUS_RANK[previous_status]
    current_rank = _COVERAGE_STATUS_RANK[current_status]
    change = "unchanged"
    if current_rank > previous_rank:
        change = "improved"
    elif current_rank < previous_rank:
        change = "regressed"
    return {
        "target_id": target_id,
        "text": str(current.get("text") or current.get("label") or previous.get("text") or previous.get("label") or "").strip(),
        "required": coverage_target_is_required(current),
        "previous_status": previous_status,
        "current_status": current_status,
        "change": change,
    }


def _target_status(target: Mapping[str, Any]) -> str:
    status = str(target.get("status") or "missing").strip().lower()
    return status if status in _COVERAGE_STATUS_RANK else "missing"


def _comparison_status(improved: list[dict], regressed: list[dict], *, contract_changed: bool) -> str:
    if contract_changed:
        return "contract_changed"
    if improved and regressed:
        return "mixed"
    if regressed:
        return "regressed"
    if improved:
        return "progressed"
    return "no_progress"


def _task_verdict_status(run: Mapping[str, Any]) -> str:
    verdict = task_verdict_from_run(run)
    return str(verdict.get("status") or "not_evaluated") if isinstance(verdict, Mapping) else "not_evaluated"


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0
