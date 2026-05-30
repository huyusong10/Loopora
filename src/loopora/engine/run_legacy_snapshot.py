from __future__ import annotations

from loopora.events.replay import RunSnapshot
from loopora.kernel.run_state import RunLifecycleStatus, RunState
from loopora.kernel.verdict import VerdictStatus


def legacy_run_snapshot(run_id: str, run: dict) -> RunSnapshot:
    return RunSnapshot(
        state=RunState(
            id=run_id,
            loop_id=str(run.get("loop_id") or ""),
            lifecycle_status=legacy_status_to_lifecycle(str(run.get("status") or "")),
            current_iteration=int(run.get("current_iter") or 0),
            current_step_id=None,
            pending_actor=None,
            stop_requested=bool(run.get("stop_requested")),
        ),
        latest_event_sequence=0,
        verdict_status=legacy_task_verdict_status(run.get("task_verdict")),
    )


def missing_run_snapshot(run_id: str) -> RunSnapshot:
    return RunSnapshot(state=RunState(id=run_id, loop_id=""), latest_event_sequence=0)


def legacy_status_to_lifecycle(status: str) -> RunLifecycleStatus:
    return {
        "queued": RunLifecycleStatus.CREATED,
        "running": RunLifecycleStatus.RUNNING,
        "awaiting_agent": RunLifecycleStatus.AWAITING_ACTOR,
        "succeeded": RunLifecycleStatus.CLOSED,
        "stopped": RunLifecycleStatus.STOPPED,
        "failed": RunLifecycleStatus.FAILED,
    }.get(status, RunLifecycleStatus.CREATED)


def legacy_task_verdict_status(value: object) -> VerdictStatus:
    if isinstance(value, dict):
        status = str(value.get("status") or "not_evaluated")
        if status == "insufficient_evidence":
            return VerdictStatus.CONTINUE_REQUIRED
        if status == "failed":
            return VerdictStatus.BLOCKED
        try:
            return VerdictStatus(status)
        except ValueError:
            return VerdictStatus.NOT_EVALUATED
    return VerdictStatus.NOT_EVALUATED
