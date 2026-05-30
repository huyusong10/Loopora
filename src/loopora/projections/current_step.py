from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.events.replay import RunSnapshot, replay_run_snapshot
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION


def replay_current_step_projection(events: list[EventEnvelope]) -> dict:
    snapshot = replay_run_snapshot(events)
    return current_step_projection(snapshot)


def current_step_projection(snapshot: RunSnapshot) -> dict:
    state = snapshot.state
    pending_actor = state.pending_actor.to_dict() if state.pending_actor else None
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_current_step",
        "source_sequence": snapshot.latest_event_sequence,
        "run_id": state.id,
        "step_id": state.current_step_id,
        "iteration": state.current_iteration,
        "pending_actor": pending_actor,
        "claimable": state.current_step_id is not None and pending_actor is not None,
        "lifecycle_status": state.lifecycle_status.value,
    }
