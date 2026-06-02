from __future__ import annotations

import json
from pathlib import Path

from loopora.db import LooporaRepository
from loopora.events.projection_cache import current_step_projection_for_run
from loopora.events.store import DomainEventAppendRequest
from loopora.events.streams import run_stream_id
from loopora.kernel import ActorRef

from current_step_projection_test_support import claim_builder_step, create_current_step_projection_run


CLAIMED_STEP_SOURCE_SEQUENCE = 4
COMMITTED_STEP_SOURCE_SEQUENCE = 7
TAMPERED_CACHE_SOURCE_SEQUENCE = 999


def test_run_engine_current_step_projection_replays_when_cache_missing(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_current_step_projection_run(repository, tmp_path)
    actor = ActorRef(kind="runner", id="headless")
    claim_builder_step(repository, run, actor)
    with repository.transaction() as connection:
        connection.execute(
            "DELETE FROM projection_store WHERE projection_name = ? AND projection_key = ?",
            ("current_step", run["id"]),
        )

    projection = current_step_projection_for_run(repository, run["id"])
    refreshed_cache = repository.get_projection_record("current_step", run["id"])

    assert projection["kind"] == "event_replayed_current_step"
    assert projection["source_sequence"] == CLAIMED_STEP_SOURCE_SEQUENCE
    assert projection["step_id"] == "builder"
    assert projection["claimable"] is True
    assert refreshed_cache["payload"] == projection


def test_run_engine_current_step_projection_replays_when_cache_is_stale(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_current_step_projection_run(repository, tmp_path)
    actor = ActorRef(kind="runner", id="headless")
    claim_builder_step(repository, run, actor)
    cached_current_step = repository.get_projection_record("current_step", run["id"])

    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepSubmitted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "status": "completed",
                "summary": "Builder completed.",
            },
            actor=actor,
        )
    )
    accepted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepAccepted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "result_status": "completed",
            },
            actor=actor,
            causation_id=submitted_event.event_id,
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepCommitted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "result_status": "completed",
            },
            actor=actor,
            causation_id=accepted_event.event_id,
        )
    )
    tampered_payload = {**cached_current_step["payload"], "source_sequence": TAMPERED_CACHE_SOURCE_SEQUENCE}
    with repository.transaction() as connection:
        connection.execute(
            """
            UPDATE projection_store
            SET payload_json = ?
            WHERE projection_name = ? AND projection_key = ?
            """,
            (json.dumps(tampered_payload), "current_step", run["id"]),
        )

    projection = current_step_projection_for_run(repository, run["id"])
    refreshed_cache = repository.get_projection_record("current_step", run["id"])

    assert cached_current_step["payload"]["source_sequence"] == CLAIMED_STEP_SOURCE_SEQUENCE
    assert projection["source_sequence"] == COMMITTED_STEP_SOURCE_SEQUENCE
    assert projection["step_id"] is None
    assert projection["claimable"] is False
    assert refreshed_cache["source_sequence"] == COMMITTED_STEP_SOURCE_SEQUENCE
    assert refreshed_cache["payload"] == projection
