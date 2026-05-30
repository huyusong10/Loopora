from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef, RunLifecycleStatus, VerdictStatus


def test_run_snapshot_source_prefers_cached_projection() -> None:
    class CachedRunSnapshotRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 9

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "run_snapshot"
            assert projection_key == "run_cached"
            return {
                "source_sequence": 9,
                "payload": {
                    "schema_version": 1,
                    "kind": "event_replayed_run_snapshot",
                    "run_id": "run_cached",
                    "loop_id": "loop_cached",
                    "lifecycle_status": "awaiting_actor",
                    "current_iteration": 3,
                    "current_step_id": "builder",
                    "pending_actor": {"kind": "agent", "id": "codex", "display_name": "codex", "adapter": "codex"},
                    "verdict_status": "continue_required",
                    "source_sequence": 9,
                }
            }

        def list_domain_events(self, stream_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cached snapshot source should not replay events for {stream_id}")

        def get_run(self, run_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cached snapshot source should not read legacy run {run_id}")

    snapshot = run_snapshot_from_repository(CachedRunSnapshotRepository(), "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR
    assert snapshot.state.current_iteration == 3
    assert snapshot.state.current_step_id == "builder"
    assert snapshot.state.pending_actor == ActorRef(kind="agent", id="codex", display_name="codex", adapter="codex")
    assert snapshot.latest_event_sequence == 9
    assert snapshot.verdict_status == VerdictStatus.CONTINUE_REQUIRED


def test_run_snapshot_source_replays_when_cached_projection_is_stale(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id("run_cached"),
            aggregate_type="run",
            aggregate_id="run_cached",
            event_type="RunCreated",
            actor=ActorRef.system(),
            payload={"run_id": "run_cached", "loop_id": "loop_cached"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id("run_cached"),
            aggregate_type="run",
            aggregate_id="run_cached",
            event_type="RunStarted",
            actor=ActorRef.system(),
            payload={"run_id": "run_cached"},
        )
    )
    repository.put_projection_record(
        "run_snapshot",
        "run_cached",
        source_sequence=1,
        payload={
            "schema_version": 1,
            "kind": "event_replayed_run_snapshot",
            "run_id": "run_cached",
            "loop_id": "loop_cached",
            "lifecycle_status": "created",
            "source_sequence": 1,
        },
    )

    snapshot = run_snapshot_from_repository(repository, "run_cached")
    refreshed_cache = repository.get_projection_record("run_snapshot", "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert snapshot.latest_event_sequence == 2
    assert refreshed_cache["source_sequence"] == 2
    assert refreshed_cache["payload"]["lifecycle_status"] == "running"
    assert refreshed_cache["payload"]["source_sequence"] == 2


def test_run_snapshot_source_ignores_cached_projection_for_different_run(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id("run_cached"),
            aggregate_type="run",
            aggregate_id="run_cached",
            event_type="RunCreated",
            actor=ActorRef.system(),
            payload={"run_id": "run_cached", "loop_id": "loop_cached"},
        )
    )
    repository.put_projection_record(
        "run_snapshot",
        "run_cached",
        source_sequence=99,
        payload={
            "schema_version": 1,
            "kind": "event_replayed_run_snapshot",
            "run_id": "other_run",
            "loop_id": "other_loop",
            "lifecycle_status": "closed",
            "source_sequence": 99,
        },
    )

    snapshot = run_snapshot_from_repository(repository, "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED
    assert snapshot.latest_event_sequence == 1


def test_run_snapshot_source_ignores_cached_projection_with_wrong_kind(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id("run_cached"),
            aggregate_type="run",
            aggregate_id="run_cached",
            event_type="RunCreated",
            actor=ActorRef.system(),
            payload={"run_id": "run_cached", "loop_id": "loop_cached"},
        )
    )
    repository.put_projection_record(
        "run_snapshot",
        "run_cached",
        source_sequence=99,
        payload={
            "schema_version": 1,
            "kind": "not_run_snapshot",
            "run_id": "run_cached",
            "loop_id": "wrong_loop",
            "lifecycle_status": "closed",
            "source_sequence": 99,
        },
    )

    snapshot = run_snapshot_from_repository(repository, "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED
    assert snapshot.latest_event_sequence == 1
