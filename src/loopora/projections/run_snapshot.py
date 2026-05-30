from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.events.replay import RunSnapshot, replay_run_snapshot
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION


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
