from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from loopora.events.envelope import EventEnvelope
from loopora.kernel.actors import ActorRef
from loopora.kernel.run_state import RunLifecycleStatus, RunState
from loopora.kernel.verdict import VerdictStatus


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    state: RunState
    latest_event_sequence: int
    verdict_status: VerdictStatus = VerdictStatus.NOT_EVALUATED


@dataclass(slots=True)
class _ReplayState:
    run_id: str
    loop_id: str = ""
    lifecycle_status: RunLifecycleStatus = RunLifecycleStatus.CREATED
    current_iteration: int = 0
    current_step_id: str | None = None
    pending_actor: ActorRef | None = None
    stop_requested: bool = False
    verdict_status: VerdictStatus = VerdictStatus.NOT_EVALUATED


def replay_run_snapshot(events: list[EventEnvelope]) -> RunSnapshot:
    if not events:
        return RunSnapshot(state=RunState(id="", loop_id=""), latest_event_sequence=0)

    state = _ReplayState(run_id=events[0].aggregate_id)
    for event in sorted(events, key=lambda item: item.sequence):
        handler = _HANDLERS.get(event.event_type)
        if handler:
            handler(state, event)

    return RunSnapshot(
        state=RunState(
            id=state.run_id,
            loop_id=state.loop_id,
            lifecycle_status=state.lifecycle_status,
            current_iteration=state.current_iteration,
            current_step_id=state.current_step_id,
            pending_actor=state.pending_actor,
            stop_requested=state.stop_requested,
        ),
        latest_event_sequence=max(event.sequence for event in events),
        verdict_status=state.verdict_status,
    )


def _coerce_verdict_status(value: object) -> VerdictStatus:
    legacy_status = str(value or "not_evaluated")
    if legacy_status == "insufficient_evidence":
        return VerdictStatus.CONTINUE_REQUIRED
    if legacy_status == "failed":
        return VerdictStatus.BLOCKED
    try:
        return VerdictStatus(legacy_status)
    except ValueError:
        return VerdictStatus.NOT_EVALUATED


def _apply_run_created(state: _ReplayState, event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.loop_id = str(event.payload.get("loop_id") or state.loop_id)
    state.lifecycle_status = RunLifecycleStatus.CREATED


def _apply_run_active(state: _ReplayState, _event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.lifecycle_status = RunLifecycleStatus.RUNNING
    state.pending_actor = None


def _apply_run_paused(state: _ReplayState, event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.lifecycle_status = RunLifecycleStatus.AWAITING_ACTOR
    state.pending_actor = ActorRef.from_dict(event.payload.get("pending_actor"))


def _apply_step_instruction(state: _ReplayState, event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.lifecycle_status = RunLifecycleStatus.AWAITING_ACTOR
    state.current_step_id = str(event.payload.get("step_id") or state.current_step_id or "")
    state.current_iteration = _event_payload_int(event, "iteration", default=state.current_iteration)
    state.pending_actor = ActorRef.from_dict(event.payload.get("pending_actor"))


def _apply_iteration_started(state: _ReplayState, event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.current_iteration = _event_payload_int(event, "iteration", default=state.current_iteration)


def _apply_step_committed(state: _ReplayState, _event: EventEnvelope) -> None:
    if _is_terminal_lifecycle(state):
        return
    state.current_step_id = None
    state.pending_actor = None


def _apply_verdict(state: _ReplayState, event: EventEnvelope) -> None:
    state.verdict_status = _coerce_verdict_status(event.payload.get("status"))


def _apply_terminal(status: RunLifecycleStatus, *, stop_requested: bool = False) -> Callable[[_ReplayState, EventEnvelope], None]:
    def apply(state: _ReplayState, _event: EventEnvelope) -> None:
        if _is_terminal_lifecycle(state):
            return
        state.lifecycle_status = status
        state.current_step_id = None
        state.stop_requested = stop_requested
        state.pending_actor = None

    return apply


def _is_terminal_lifecycle(state: _ReplayState) -> bool:
    return state.lifecycle_status in {
        RunLifecycleStatus.CLOSED,
        RunLifecycleStatus.STOPPED,
        RunLifecycleStatus.FAILED,
    }


def _event_payload_int(event: EventEnvelope, key: str, *, default: int) -> int:
    value = event.payload.get(key)
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_HANDLERS: dict[str, Callable[[_ReplayState, EventEnvelope], None]] = {
    "RunCreated": _apply_run_created,
    "RunStarted": _apply_run_active,
    "RunResumed": _apply_run_active,
    "RunPausedForActor": _apply_run_paused,
    "StepInstructionIssued": _apply_step_instruction,
    "IterationStarted": _apply_iteration_started,
    "StepCommitted": _apply_step_committed,
    "VerdictIssued": _apply_verdict,
    "RunClosed": _apply_terminal(RunLifecycleStatus.CLOSED),
    "RunStopped": _apply_terminal(RunLifecycleStatus.STOPPED, stop_requested=True),
    "RunFailed": _apply_terminal(RunLifecycleStatus.FAILED),
}
