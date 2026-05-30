from __future__ import annotations

from loopora.events.projection_cache import current_step_projection_for_run
from loopora.events.streams import run_stream_id


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
