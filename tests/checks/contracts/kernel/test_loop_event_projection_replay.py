from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id
from loopora.projections import replay_loop_projection_bundle

from loop_event_core_test_support import create_loop, gatekeeper_loop_spec


ACTIVE_LOOP_PROJECTION_SOURCE_SEQUENCE = 3
ARCHIVED_LOOP_PROJECTION_SOURCE_SEQUENCE = 4


def test_loop_events_replay_loop_definition_projection(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    create_loop(
        repository,
        tmp_path,
        gatekeeper_loop_spec(
            loop_id="loop_replay_projection",
            name="Loop Replay Projection",
            task="Replay loop definition.",
        ),
    )

    projections = replay_loop_projection_bundle(repository.list_domain_events(loop_stream_id("loop_replay_projection")))
    cached = repository.get_projection_record("loop_definition", "loop_replay_projection")
    cached_timeline = repository.get_projection_record("audit_timeline", "loop_replay_projection")

    assert projections["loop_definition"] == {
        "schema_version": 1,
        "kind": "event_replayed_loop_definition",
        "source_sequence": ACTIVE_LOOP_PROJECTION_SOURCE_SEQUENCE,
        "loop_id": "loop_replay_projection",
        "name": "Loop Replay Projection",
        "task": "Replay loop definition.",
        "completion_mode": "gatekeeper",
        "status": "active",
        "check_count": 1,
        "coverage_target_count": 2,
        "role_count": 1,
        "step_count": 1,
        "finish_step_ids": ["judge"],
    }
    assert cached["source_sequence"] == ACTIVE_LOOP_PROJECTION_SOURCE_SEQUENCE
    assert cached["payload"] == projections["loop_definition"]
    assert cached_timeline["source_sequence"] == ACTIVE_LOOP_PROJECTION_SOURCE_SEQUENCE
    assert cached_timeline["payload"] == projections["audit_timeline"]
    assert [event["event_type"] for event in projections["audit_timeline"]["events"]] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
    ]

    repository.delete_loop("loop_replay_projection")

    archived = replay_loop_projection_bundle(repository.list_domain_events(loop_stream_id("loop_replay_projection")))

    assert archived["loop_definition"]["source_sequence"] == ARCHIVED_LOOP_PROJECTION_SOURCE_SEQUENCE
    assert archived["loop_definition"]["status"] == "archived"
    assert repository.get_projection_record("loop_definition", "loop_replay_projection")["payload"]["status"] == "archived"
    assert [event["event_type"] for event in archived["audit_timeline"]["events"]] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopArchived",
    ]
