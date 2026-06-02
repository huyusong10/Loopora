from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef, RunLifecycleStatus


REFRESHED_RUN_SOURCE_SEQUENCE = 2
STALE_RUN_CACHE_SOURCE_SEQUENCE = 1
UNRELATED_RUN_CACHE_SOURCE_SEQUENCE = 99


def test_run_snapshot_source_replays_when_cached_projection_is_stale(tmp_path: Path) -> None:
    repository = _repository_with_created_run(tmp_path, run_id="run_cached", loop_id="loop_cached")
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
    _put_cached_snapshot(repository, source_sequence=STALE_RUN_CACHE_SOURCE_SEQUENCE)

    snapshot = run_snapshot_from_repository(repository, "run_cached")
    refreshed_cache = repository.get_projection_record("run_snapshot", "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert snapshot.latest_event_sequence == REFRESHED_RUN_SOURCE_SEQUENCE
    assert refreshed_cache["source_sequence"] == REFRESHED_RUN_SOURCE_SEQUENCE
    assert refreshed_cache["payload"]["lifecycle_status"] == "running"
    assert refreshed_cache["payload"]["source_sequence"] == REFRESHED_RUN_SOURCE_SEQUENCE


def test_run_snapshot_source_ignores_cached_projection_for_different_run(tmp_path: Path) -> None:
    repository = _repository_with_created_run(tmp_path, run_id="run_cached", loop_id="loop_cached")
    _put_cached_snapshot(
        repository,
        source_sequence=UNRELATED_RUN_CACHE_SOURCE_SEQUENCE,
        overrides={"run_id": "other_run", "loop_id": "other_loop", "lifecycle_status": "closed"},
    )

    snapshot = run_snapshot_from_repository(repository, "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED
    assert snapshot.latest_event_sequence == 1


def test_run_snapshot_source_ignores_cached_projection_with_wrong_kind(tmp_path: Path) -> None:
    repository = _repository_with_created_run(tmp_path, run_id="run_cached", loop_id="loop_cached")
    _put_cached_snapshot(
        repository,
        source_sequence=UNRELATED_RUN_CACHE_SOURCE_SEQUENCE,
        overrides={"kind": "not_run_snapshot", "loop_id": "wrong_loop", "lifecycle_status": "closed"},
    )

    snapshot = run_snapshot_from_repository(repository, "run_cached")

    assert snapshot.state.id == "run_cached"
    assert snapshot.state.loop_id == "loop_cached"
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED
    assert snapshot.latest_event_sequence == 1


def _repository_with_created_run(tmp_path: Path, *, run_id: str, loop_id: str) -> LooporaRepository:
    repository = LooporaRepository(tmp_path / "app.db")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run_id),
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            actor=ActorRef.system(),
            payload={"run_id": run_id, "loop_id": loop_id},
        )
    )
    return repository


def _put_cached_snapshot(
    repository: LooporaRepository,
    *,
    source_sequence: int,
    overrides: dict[str, object] | None = None,
) -> None:
    payload = {
        "schema_version": 1,
        "kind": "event_replayed_run_snapshot",
        "run_id": "run_cached",
        "loop_id": "loop_cached",
        "lifecycle_status": "created",
        "source_sequence": source_sequence,
    }
    payload.update(overrides or {})
    repository.put_projection_record(
        "run_snapshot",
        "run_cached",
        source_sequence=source_sequence,
        payload=payload,
    )
