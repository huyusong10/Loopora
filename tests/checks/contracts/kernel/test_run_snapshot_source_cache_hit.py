from __future__ import annotations

from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.events import run_stream_id
from loopora.kernel import ActorRef, RunLifecycleStatus, VerdictStatus


CACHED_RUN_CURRENT_ITERATION = 3
CACHED_RUN_SOURCE_SEQUENCE = 9


def test_run_snapshot_source_prefers_cached_projection() -> None:
    class CachedRunSnapshotRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return CACHED_RUN_SOURCE_SEQUENCE

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "run_snapshot"
            assert projection_key == "run_cached"
            return {
                "source_sequence": CACHED_RUN_SOURCE_SEQUENCE,
                "payload": {
                    "schema_version": 1,
                    "kind": "event_replayed_run_snapshot",
                    "run_id": "run_cached",
                    "loop_id": "loop_cached",
                    "lifecycle_status": "awaiting_actor",
                    "current_iteration": CACHED_RUN_CURRENT_ITERATION,
                    "current_step_id": "builder",
                    "pending_actor": {"kind": "agent", "id": "codex", "display_name": "codex", "adapter": "codex"},
                    "verdict_status": "continue_required",
                    "source_sequence": CACHED_RUN_SOURCE_SEQUENCE,
                },
            }

        def list_domain_events(self, stream_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cached snapshot source should not replay events for {stream_id}")

        def get_run(self, run_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cached snapshot source should not read legacy run {run_id}")

    snapshot = run_snapshot_from_repository(CachedRunSnapshotRepository(), "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR
    assert snapshot.state.current_iteration == CACHED_RUN_CURRENT_ITERATION
    assert snapshot.state.current_step_id == "builder"
    assert snapshot.state.pending_actor == ActorRef(kind="agent", id="codex", display_name="codex", adapter="codex")
    assert snapshot.latest_event_sequence == CACHED_RUN_SOURCE_SEQUENCE
    assert snapshot.verdict_status == VerdictStatus.CONTINUE_REQUIRED
