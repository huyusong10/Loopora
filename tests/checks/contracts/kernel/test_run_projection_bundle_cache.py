from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineIssueVerdictRequest
from loopora.events.projection_cache import (
    RUN_IDENTITY_PROJECTION_NAMES,
    RUN_PROJECTION_KINDS,
    rebuild_run_projection_cache,
    run_projection_bundle_for_run,
)
from loopora.events.streams import run_stream_id
from loopora.kernel import ActorRef
from loopora.projections import replay_run_projection_bundle

from kernel_event_test_support import create_kernel_run


FAKE_RUN_PROJECTION_SOURCE_SEQUENCE = 7


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_projection_cache",
            "loop_id": "loop_projection_cache",
            "loop_name": "Projection Cache Loop",
            "task": "Prove projection cache.",
        },
    )


class FakeRunProjectionRepository:
    def __init__(
        self,
        *,
        run_id: str = "run_cached",
        source_sequence: int = FAKE_RUN_PROJECTION_SOURCE_SEQUENCE,
        wrong_identity_projection: str | None = None,
        refresh_enabled: bool = False,
    ) -> None:
        self.run_id = run_id
        self.source_sequence = source_sequence
        self.wrong_identity_projection = wrong_identity_projection
        self.refresh_enabled = refresh_enabled

    def latest_domain_event_sequence(self, stream_id: str) -> int:
        assert stream_id == run_stream_id(self.run_id)
        return self.source_sequence

    def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
        assert projection_name in RUN_PROJECTION_KINDS
        assert projection_key == self.run_id
        payload = {
            "schema_version": 1,
            "kind": RUN_PROJECTION_KINDS[projection_name],
            "source_sequence": self.source_sequence,
            "projection_name": projection_name,
        }
        if projection_name in RUN_IDENTITY_PROJECTION_NAMES:
            payload["run_id"] = "other_run" if projection_name == self.wrong_identity_projection else self.run_id
        return {"source_sequence": self.source_sequence, "payload": payload}

    def refresh_run_projection_cache(self, run_id: str) -> dict:
        assert run_id == self.run_id
        if not self.refresh_enabled:
            raise AssertionError(f"cache hit should not rebuild projections for {run_id}")
        return {
            projection_name: {
                "schema_version": 1,
                "kind": kind,
                "run_id": run_id,
                "source_sequence": self.source_sequence,
                "refreshed": True,
            }
            for projection_name, kind in RUN_PROJECTION_KINDS.items()
        }


def test_run_projection_cache_metadata_matches_replay_bundle() -> None:
    replayed = replay_run_projection_bundle([])

    assert set(RUN_PROJECTION_KINDS) == set(replayed)
    assert {name: replayed[name]["kind"] for name in replayed} == RUN_PROJECTION_KINDS


def test_run_projection_bundle_cache_hit_uses_one_consistent_source_sequence() -> None:
    bundle = run_projection_bundle_for_run(FakeRunProjectionRepository(), "run_cached")

    assert set(bundle) == set(RUN_PROJECTION_KINDS)
    assert all(payload["source_sequence"] == FAKE_RUN_PROJECTION_SOURCE_SEQUENCE for payload in bundle.values())
    assert bundle["task_verdict"]["projection_name"] == "task_verdict"


def test_run_projection_bundle_prefers_fresh_projection_store_without_rebuild(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    def fail_rebuild(_run_id: str) -> dict:
        raise AssertionError("fresh projection_store records should be used without rebuilding")

    monkeypatch.setattr(repository, "refresh_run_projection_cache", fail_rebuild)

    projections = run_projection_bundle_for_run(repository, run["id"])

    assert projections["run_snapshot"]["run_id"] == run["id"]
    assert projections["coverage"]["source_sequence"] == 1
    assert projections["task_verdict"]["source_sequence"] == 1


def test_run_projection_bundle_rebuilds_when_any_cached_projection_has_wrong_run_identity() -> None:
    repository = FakeRunProjectionRepository(wrong_identity_projection="run_snapshot", refresh_enabled=True)

    bundle = run_projection_bundle_for_run(repository, "run_cached")

    assert set(bundle) == set(RUN_PROJECTION_KINDS)
    assert all(payload["source_sequence"] == FAKE_RUN_PROJECTION_SOURCE_SEQUENCE for payload in bundle.values())
    assert all(payload["refreshed"] is True for payload in bundle.values())


def test_run_engine_rebuilds_projection_store_from_event_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=ActorRef(kind="system", id="verdict-engine"),
            verdict={"status": "continue_required", "source": "system", "summary": "Need more proof."},
        )
    )

    rebuild_run_projection_cache(repository, run["id"])
    cached = repository.get_projection_record("task_verdict", run["id"])

    assert cached["source_sequence"] == repository.latest_domain_event_sequence(run_stream_id(run["id"]))
    assert cached["payload"]["status"] == "continue_required"
