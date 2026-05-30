from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from loopora.events.replay import RunSnapshot
from loopora.kernel.actors import ActorRef
from loopora.kernel.run_state import RunLifecycleStatus
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
