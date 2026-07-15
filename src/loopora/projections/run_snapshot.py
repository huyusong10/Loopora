from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.events.replay import RunSnapshot, replay_run_snapshot
from loopora.kernel import ActorRef, RunLifecycleStatus, RunState, VerdictStatus
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION
from loopora.utils import coerced_int


def replay_run_snapshot_projection(events: list[EventEnvelope]) -> dict:
    snapshot = replay_run_snapshot(events)
    return run_snapshot_projection(snapshot)


def run_snapshot_projection(snapshot: RunSnapshot) -> dict:
    state = snapshot.state
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_run_snapshot",
        "source_sequence": snapshot.latest_event_sequence,
        "run_id": state.id,
        "loop_id": state.loop_id,
        "lifecycle_status": state.lifecycle_status.value,
        "current_iteration": state.current_iteration,
        "current_step_id": state.current_step_id,
        "pending_actor": state.pending_actor.to_dict() if state.pending_actor else None,
        "stop_requested": state.stop_requested,
        "verdict_status": snapshot.verdict_status.value,
    }


def run_snapshot_from_projection(payload: object) -> RunSnapshot | None:
    if not isinstance(payload, dict):
        return None
    if coerced_int(payload.get("schema_version"), default=0) != EVENT_REPLAY_PROJECTION_SCHEMA_VERSION:
        return None
    if payload.get("kind") != "event_replayed_run_snapshot":
        return None
    run_id = str(payload.get("run_id") or "").strip()
    if not run_id:
        return None
    try:
        lifecycle_status = RunLifecycleStatus(str(payload.get("lifecycle_status") or RunLifecycleStatus.CREATED.value))
    except ValueError:
        return None
    try:
        verdict_status = VerdictStatus(str(payload.get("verdict_status") or VerdictStatus.NOT_EVALUATED.value))
    except ValueError:
        verdict_status = VerdictStatus.NOT_EVALUATED
    pending_actor_payload = payload.get("pending_actor")
    pending_actor = ActorRef.from_dict(pending_actor_payload) if isinstance(pending_actor_payload, dict) else None
    current_step_id = _optional_text(payload.get("current_step_id"))
    return RunSnapshot(
        state=RunState(
            id=run_id,
            loop_id=str(payload.get("loop_id") or ""),
            lifecycle_status=lifecycle_status,
            current_iteration=coerced_int(payload.get("current_iteration"), default=0),
            current_step_id=current_step_id,
            pending_actor=pending_actor,
            stop_requested=bool(payload.get("stop_requested")),
        ),
        latest_event_sequence=coerced_int(payload.get("source_sequence"), default=0),
        verdict_status=verdict_status,
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
