from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_entry_continuation import (
    run_continuation_context_for_terminal_run,
    task_verdict_status_for_run,
)
from loopora.context_step_instruction_normalizers import (
    empty_continuation_context,
    normalize_continuation_context,
)
from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.run_continuation_progress import (
    build_continuation_progress_context,
    continuation_action_mode,
)
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_types import ACTIVE_WORKDIR_CONFLICT_MESSAGE, LooporaConflictError, LooporaError, TERMINAL_RUN_STATUSES
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES
from loopora.utils import read_json, write_json

ADVISORY_FOLLOW_UP_KIND = "advisory"
ADVISORY_FOLLOW_UP_REASON = "recorded_advisory_follow_up"
EVIDENCE_CONTINUATION_REASON = "terminal_task_verdict_requires_next_run"
LIFECYCLE_RETRY_REASON = "previous_lifecycle_failure_retry"
ADVISORY_FOLLOW_UP_UNAVAILABLE = "recorded advisory follow-up is unavailable for this run"
FOLLOW_UP_STATUS_ACTIVE = "active"
FOLLOW_UP_STATUS_BLOCKED = "blocked"
FOLLOW_UP_STATUS_COMPLETED = "completed"
FOLLOW_UP_STATUS_NO_PROGRESS = "no_progress"
FOLLOW_UP_STATUS_PROGRESSED = "progressed"


class ServiceRunContinuationMixin:
    def start_next_run(
        self,
        loop_id: str,
        *,
        follow_up_kind: str = "",
    ) -> dict:
        previous_runs = self.repository.list_runs_for_loop(loop_id, limit=1)
        if not previous_runs:
            if str(follow_up_kind or "").strip():
                raise LooporaConflictError(ADVISORY_FOLLOW_UP_UNAVAILABLE)
            return self.start_run(loop_id)
        previous_run = previous_runs[0]
        if previous_run["status"] not in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(ACTIVE_WORKDIR_CONFLICT_MESSAGE)
        return self._start_run_from_previous(previous_run, follow_up_kind=follow_up_kind)

    def rerun_from_run(
        self,
        run_id: str,
        *,
        follow_up_kind: str = "",
        background: bool = False,
    ) -> dict:
        previous_run = self.get_run(run_id)
        if previous_run["status"] not in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(f"cannot rerun from active run in status {previous_run['status']}")
        run = self._start_run_from_previous(previous_run, follow_up_kind=follow_up_kind)
        return self._execute_started_continuation_run(run, background=background)

    def run_continuation_state(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        try:
            run_contract = read_json(layout.run_contract_path)
        except (OSError, UnicodeError, ValueError):
            return empty_continuation_context()
        source = run_contract.get("continuation_context") if isinstance(run_contract, dict) else None
        return normalize_continuation_context(source)

    def run_continuation_outcome(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        continuation = self.run_continuation_state(run_id)
        if continuation.get("active") is not True or continuation.get("focus_kind") != ADVISORY_FOLLOW_UP_KIND:
            return {}
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        try:
            current_coverage = read_json(layout.evidence_coverage_path)
        except (OSError, UnicodeError, ValueError):
            current_coverage = {}
        current_targets = {
            str(item.get("id") or item.get("target_id") or "").strip(): item
            for item in list(current_coverage.get("targets") or [])
            if isinstance(item, dict) and str(item.get("id") or item.get("target_id") or "").strip()
        }
        comparisons = [
            _follow_up_target_comparison(target, current_targets.get(str(target.get("target_id") or "").strip()))
            for target in continuation["focus_targets"]
        ]
        improved_count = sum(item["improved"] for item in comparisons)
        resolved_count = sum(item["current_status"] == "covered" for item in comparisons)
        blocked_count = sum(item["current_status"] == "blocked" for item in comparisons)
        focus_target_count = int(continuation.get("focus_target_count") or 0)
        status = _follow_up_outcome_status(
            run_status=str(run.get("status") or ""),
            focus_target_count=focus_target_count,
            comparisons=comparisons,
        )
        return {
            "available": True,
            "status": status,
            "reason": continuation["reason"],
            "previous_run_id": continuation["previous_run_id"],
            "focus_kind": continuation["focus_kind"],
            "focus_target_count": focus_target_count,
            "tracked_target_count": len(comparisons),
            "improved_target_count": improved_count,
            "resolved_target_count": resolved_count,
            "blocked_target_count": blocked_count,
            "remaining_target_count": max(focus_target_count - resolved_count, 0),
            "targets": comparisons,
        }

    def _seed_run_continuation_context(
        self,
        run: dict,
        previous_run: dict,
        *,
        reason: str = "",
        focus_kind: str = "unresolved",
    ) -> dict[str, Any]:
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        previous_layout = self._run_artifact_layout(Path(previous_run["runs_dir"]))
        continuation = run_continuation_context_for_terminal_run(
            previous_run,
            previous_layout,
            reason=reason,
            focus_kind=focus_kind,
        )
        progress = build_continuation_progress_context(
            self.repository.list_runs_for_loop(str(previous_run["loop_id"]), limit=3),
            source_run_id=str(previous_run["id"]),
            current_run_id=str(run["id"]),
        )
        continuation["prior_run_progress"] = progress
        continuation["action_mode"] = continuation_action_mode(
            reason=str(continuation["reason"]),
            progress_status=str(progress["status"]),
        )
        continuation_path = layout.context_dir / "continuation_context.json"
        write_json(continuation_path, continuation)

        run_contract = read_json(layout.run_contract_path)
        if isinstance(run_contract, dict):
            run_contract["continuation_context"] = continuation
            write_json(layout.run_contract_path, run_contract)

        self.append_run_event(
            run["id"],
            "run_continuation_context_seeded",
            {
                "reason": continuation["reason"],
                "previous_run_id": continuation["previous_run_id"],
                "previous_run_status": continuation["previous_run_status"],
                "previous_task_verdict_status": continuation["previous_task_verdict"]["status"],
                "missing_check_count": continuation["coverage"]["missing_check_count"],
                "top_gap_count": len(continuation["coverage"]["top_gaps"]),
                "focus_kind": continuation["focus_kind"],
                "focus_target_count": continuation["focus_target_count"],
                "focus_target_ids": [item["target_id"] for item in continuation["focus_targets"]],
                "action_mode": continuation["action_mode"],
                "prior_run_progress_status": progress["status"],
                "prior_run_id": progress["prior_run_id"],
                "continuation_context_path": layout.relative(continuation_path),
            },
        )
        return continuation

    def _run_continuation_request(self, previous_run: dict, *, follow_up_kind: str) -> dict[str, str]:
        normalized_kind = str(follow_up_kind or "").strip().lower()
        if normalized_kind and normalized_kind != ADVISORY_FOLLOW_UP_KIND:
            raise LooporaConflictError(f"unknown run follow-up kind: {normalized_kind}")
        if normalized_kind == ADVISORY_FOLLOW_UP_KIND:
            acceptance_state = self.run_result_acceptance_state(str(previous_run["id"]))
            if acceptance_state.get("recorded_advisory_follow_up_available") is not True:
                raise LooporaConflictError(ADVISORY_FOLLOW_UP_UNAVAILABLE)
            return {"reason": ADVISORY_FOLLOW_UP_REASON, "focus_kind": ADVISORY_FOLLOW_UP_KIND}
        acceptance_state = self.run_result_acceptance_state(str(previous_run["id"]))
        if acceptance_state.get("accepted") is True:
            return {}
        if run_result_is_lifecycle_failure(previous_run):
            return {"reason": LIFECYCLE_RETRY_REASON, "focus_kind": "unresolved"}
        if task_verdict_status_for_run(previous_run) not in PASSING_TASK_VERDICT_STATUSES:
            return {"reason": EVIDENCE_CONTINUATION_REASON, "focus_kind": "unresolved"}
        return {}

    def _start_run_from_previous(self, previous_run: dict, *, follow_up_kind: str) -> dict:
        continuation = self._run_continuation_request(previous_run, follow_up_kind=follow_up_kind)
        run = self.start_run(str(previous_run["loop_id"]))
        if continuation:
            self._seed_run_continuation_context(run, previous_run, **continuation)
        return run

    def _execute_started_continuation_run(self, run: dict, *, background: bool) -> dict:
        if not background:
            return self.execute_run(run["id"])
        try:
            self.start_run_async(run["id"])
        except LooporaError as exc:
            if str(exc) != BACKGROUND_WORKER_START_ERROR:
                raise
            return {**self.get_run(run["id"]), "run_start_error": str(exc)}
        return run


def _follow_up_target_comparison(previous: dict[str, Any], current: object) -> dict[str, Any]:
    current_target = current if isinstance(current, dict) else {}
    previous_status = str(previous.get("status") or "missing").strip().lower() or "missing"
    current_status = str(current_target.get("status") or "missing").strip().lower() or "missing"
    return {
        "target_id": str(previous.get("target_id") or "").strip(),
        "text": str(previous.get("text") or "").strip(),
        "previous_status": previous_status,
        "current_status": current_status,
        "improved": _coverage_status_rank(current_status) > _coverage_status_rank(previous_status),
        "current_reason": str(current_target.get("reason") or "").strip(),
        "current_evidence_refs": [str(item).strip() for item in list(current_target.get("evidence_refs") or []) if str(item).strip()][:8],
        "required": coverage_target_is_required(previous),
    }


def _follow_up_outcome_status(
    *,
    run_status: str,
    focus_target_count: int,
    comparisons: list[dict[str, Any]],
) -> str:
    if run_status not in TERMINAL_RUN_STATUSES:
        return FOLLOW_UP_STATUS_ACTIVE
    resolved_count = sum(item["current_status"] == "covered" for item in comparisons)
    if focus_target_count > 0 and len(comparisons) == focus_target_count and resolved_count == focus_target_count:
        return FOLLOW_UP_STATUS_COMPLETED
    if any(item["improved"] for item in comparisons):
        return FOLLOW_UP_STATUS_PROGRESSED
    if any(item["current_status"] == "blocked" for item in comparisons):
        return FOLLOW_UP_STATUS_BLOCKED
    return FOLLOW_UP_STATUS_NO_PROGRESS


def _coverage_status_rank(status: str) -> int:
    return {"blocked": -1, "missing": 0, "weak": 1, "covered": 2}.get(status, 0)
