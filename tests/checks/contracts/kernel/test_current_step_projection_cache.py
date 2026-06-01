from __future__ import annotations

from loopora.events.projection_cache import (
    RUN_IDENTITY_PROJECTION_NAMES,
    RUN_PROJECTION_KINDS,
    current_step_projection_for_run,
    run_projection_bundle_for_run,
)
from loopora.events.streams import run_stream_id
from loopora.projections import replay_run_projection_bundle


def test_run_projection_cache_metadata_matches_replay_bundle() -> None:
    replayed = replay_run_projection_bundle([])

    assert set(RUN_PROJECTION_KINDS) == set(replayed)
    assert {name: replayed[name]["kind"] for name in replayed} == RUN_PROJECTION_KINDS


def test_run_projection_bundle_cache_hit_uses_one_consistent_source_sequence() -> None:
    class CachedRunProjectionRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 7

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name in RUN_PROJECTION_KINDS
            assert projection_key == "run_cached"
            payload = {
                "schema_version": 1,
                "kind": RUN_PROJECTION_KINDS[projection_name],
                "source_sequence": 7,
                "projection_name": projection_name,
            }
            if projection_name in RUN_IDENTITY_PROJECTION_NAMES:
                payload["run_id"] = "run_cached"
            return {
                "source_sequence": 7,
                "payload": payload,
            }

        def refresh_run_projection_cache(self, run_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cache hit should not rebuild projections for {run_id}")

    bundle = run_projection_bundle_for_run(CachedRunProjectionRepository(), "run_cached")

    assert set(bundle) == set(RUN_PROJECTION_KINDS)
    assert all(payload["source_sequence"] == 7 for payload in bundle.values())
    assert bundle["task_verdict"]["projection_name"] == "task_verdict"


def test_run_projection_bundle_rebuilds_when_any_cached_projection_has_wrong_run_identity() -> None:
    class WrongRunProjectionRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 7

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name in RUN_PROJECTION_KINDS
            assert projection_key == "run_cached"
            cached_run_id = "other_run" if projection_name == "run_snapshot" else "run_cached"
            payload = {
                "schema_version": 1,
                "kind": RUN_PROJECTION_KINDS[projection_name],
                "source_sequence": 7,
            }
            if projection_name in RUN_IDENTITY_PROJECTION_NAMES:
                payload["run_id"] = cached_run_id
            return {
                "source_sequence": 7,
                "payload": payload,
            }

        def refresh_run_projection_cache(self, run_id: str) -> dict:
            assert run_id == "run_cached"
            return {
                projection_name: {
                    "schema_version": 1,
                    "kind": kind,
                    "run_id": run_id,
                    "source_sequence": 7,
                    "refreshed": True,
                }
                for projection_name, kind in RUN_PROJECTION_KINDS.items()
            }

    bundle = run_projection_bundle_for_run(WrongRunProjectionRepository(), "run_cached")

    assert set(bundle) == set(RUN_PROJECTION_KINDS)
    assert all(payload["source_sequence"] == 7 for payload in bundle.values())
    assert all(payload["refreshed"] is True for payload in bundle.values())


def test_current_step_projection_cache_hit_uses_latest_sequence_without_replaying_events() -> None:
    class CachedCurrentStepRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 5

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "current_step"
            assert projection_key == "run_cached"
            return {
                "source_sequence": 5,
                "payload": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "run_cached",
                    "step_id": "builder",
                    "iteration": 1,
                    "claimable": True,
                    "source_sequence": 5,
                },
            }

        def list_domain_events(self, stream_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cache hit should not replay events for {stream_id}")

        def refresh_run_projection_cache(self, run_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"cache hit should not rebuild projections for {run_id}")

    projection = current_step_projection_for_run(CachedCurrentStepRepository(), "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"
    assert projection["source_sequence"] == 5


def test_current_step_projection_ignores_cached_payload_for_different_run() -> None:
    class MismatchedCurrentStepRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 5

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "current_step"
            assert projection_key == "run_cached"
            return {
                "source_sequence": 5,
                "payload": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "other_run",
                    "step_id": "wrong_builder",
                    "claimable": True,
                    "source_sequence": 5,
                },
            }

        def refresh_run_projection_cache(self, run_id: str) -> dict:
            assert run_id == "run_cached"
            return {
                "current_step": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "run_cached",
                    "step_id": "builder",
                    "claimable": True,
                    "source_sequence": 5,
                }
            }

        def list_domain_events(self, stream_id: str):  # pragma: no cover - failure path for this contract.
            raise AssertionError(f"current-step source should rebuild through projection cache for {stream_id}")

    projection = current_step_projection_for_run(MismatchedCurrentStepRepository(), "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"


def test_current_step_projection_ignores_cached_payload_with_wrong_kind() -> None:
    class WrongKindCurrentStepRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 5

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "current_step"
            assert projection_key == "run_cached"
            return {
                "source_sequence": 5,
                "payload": {
                    "schema_version": 1,
                    "kind": "not_current_step",
                    "run_id": "run_cached",
                    "step_id": "wrong_builder",
                    "claimable": True,
                    "source_sequence": 5,
                },
            }

        def refresh_run_projection_cache(self, run_id: str) -> dict:
            assert run_id == "run_cached"
            return {
                "current_step": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "run_cached",
                    "step_id": "builder",
                    "claimable": True,
                    "source_sequence": 5,
                }
            }

    projection = current_step_projection_for_run(WrongKindCurrentStepRepository(), "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"


def test_current_step_projection_ignores_future_source_sequence_cache() -> None:
    class FutureSequenceCurrentStepRepository:
        def latest_domain_event_sequence(self, stream_id: str) -> int:
            assert stream_id == run_stream_id("run_cached")
            return 5

        def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
            assert projection_name == "current_step"
            assert projection_key == "run_cached"
            return {
                "source_sequence": 6,
                "payload": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "run_cached",
                    "step_id": "stale_builder",
                    "claimable": True,
                    "source_sequence": 6,
                },
            }

        def refresh_run_projection_cache(self, run_id: str) -> dict:
            assert run_id == "run_cached"
            return {
                "current_step": {
                    "schema_version": 1,
                    "kind": "event_replayed_current_step",
                    "run_id": "run_cached",
                    "step_id": "builder",
                    "claimable": True,
                    "source_sequence": 5,
                }
            }

    projection = current_step_projection_for_run(FutureSequenceCurrentStepRepository(), "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"
    assert projection["source_sequence"] == 5
