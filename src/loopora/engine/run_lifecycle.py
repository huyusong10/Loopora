from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from loopora.events.replay import RunSnapshot
from loopora.kernel.actors import ActorRef
from loopora.kernel.run_state import RunLifecycleStatus, RunState
from loopora.kernel.verdict import VerdictStatus


class RunEngineAdvanceStatus(StrEnum):
    RUNNING = "running"
    AWAITING_ACTOR = "awaiting_actor"
    READY_FOR_STEP = "ready_for_step"
    CLOSED = "closed"
    STOPPED = "stopped"
    FAILED = "failed"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class RunEngineAdvanceOutcome:
    run_id: str
    status: RunEngineAdvanceStatus
    snapshot: RunSnapshot
    next_action: str
    current_step_id: str | None = None
    pending_actor: ActorRef | None = None
    verdict_status: VerdictStatus = VerdictStatus.NOT_EVALUATED


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


def advance_outcome_for_snapshot(snapshot: RunSnapshot) -> RunEngineAdvanceOutcome:
    status = advance_status_for_snapshot(snapshot)
    return advance_outcome(snapshot, status, next_action=next_action_for_status(status))


def advance_status_for_snapshot(snapshot: RunSnapshot) -> RunEngineAdvanceStatus:
    lifecycle_status = snapshot.state.lifecycle_status
    if lifecycle_status == RunLifecycleStatus.CLOSED:
        return RunEngineAdvanceStatus.CLOSED
    if lifecycle_status == RunLifecycleStatus.STOPPED:
        return RunEngineAdvanceStatus.STOPPED
    if lifecycle_status == RunLifecycleStatus.FAILED:
        return RunEngineAdvanceStatus.FAILED
    if lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR or snapshot.state.current_step_id:
        return RunEngineAdvanceStatus.AWAITING_ACTOR
    if lifecycle_status == RunLifecycleStatus.RUNNING:
        return RunEngineAdvanceStatus.READY_FOR_STEP
    return RunEngineAdvanceStatus.RUNNING


def next_action_for_status(status: RunEngineAdvanceStatus) -> str:
    return {
        RunEngineAdvanceStatus.CLOSED: "complete",
        RunEngineAdvanceStatus.STOPPED: "stopped",
        RunEngineAdvanceStatus.FAILED: "failed",
        RunEngineAdvanceStatus.AWAITING_ACTOR: "await_actor_submit",
        RunEngineAdvanceStatus.READY_FOR_STEP: "claim_step",
        RunEngineAdvanceStatus.MISSING: "missing",
    }.get(status, "start")


def advance_outcome(snapshot: RunSnapshot, status: RunEngineAdvanceStatus, *, next_action: str) -> RunEngineAdvanceOutcome:
    return RunEngineAdvanceOutcome(
        run_id=snapshot.state.id,
        status=status,
        snapshot=snapshot,
        next_action=next_action,
        current_step_id=snapshot.state.current_step_id,
        pending_actor=snapshot.state.pending_actor,
        verdict_status=snapshot.verdict_status,
    )
