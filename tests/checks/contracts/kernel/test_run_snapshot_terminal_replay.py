from __future__ import annotations

from loopora.events import replay_run_snapshot, run_stream_id
from loopora.events.envelope import EventEnvelope
from loopora.kernel import ActorRef, RunLifecycleStatus


def test_run_snapshot_replay_keeps_terminal_lifecycle_after_later_reopen_events() -> None:
    events = [
        _run_event(1, "RunCreated", {"run_id": "run_terminal_replay", "loop_id": "loop_terminal_replay"}),
        _run_event(2, "RunClosed", {"run_id": "run_terminal_replay"}),
        _run_event(3, "RunStarted", {"run_id": "run_terminal_replay"}),
        _run_event(4, "StepInstructionIssued", {"run_id": "run_terminal_replay", "step_id": "builder"}),
    ]

    snapshot = replay_run_snapshot(events)

    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CLOSED
    assert snapshot.state.current_step_id is None
    assert snapshot.state.pending_actor is None


def _run_event(sequence: int, event_type: str, payload: dict) -> EventEnvelope:
    return EventEnvelope.from_record(
        {
            "event_id": f"event_{sequence}",
            "stream_id": run_stream_id("run_terminal_replay"),
            "aggregate_type": "run",
            "aggregate_id": "run_terminal_replay",
            "sequence": sequence,
            "event_type": event_type,
            "actor": ActorRef.system().to_dict(),
            "correlation_id": f"event_{sequence}",
            "payload": payload,
        }
    )
