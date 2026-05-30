from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id, run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_run_event_payload_run_id_must_match_aggregate_id(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_payload_identity_boundary"

    with pytest.raises(ValueError, match="payload run_id must match aggregate_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(run_id),
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunStarted",
                payload={"run_id": "other_run"},
            )
        )


def test_loop_event_payload_loop_id_must_match_aggregate_id(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    loop_id = "loop_payload_identity_boundary"

    with pytest.raises(ValueError, match="payload loop_id must match aggregate_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id(loop_id),
                aggregate_type="loop",
                aggregate_id=loop_id,
                event_type="LoopArchived",
                payload={"loop_id": "other_loop"},
            )
        )


def test_core_event_causation_id_must_reference_existing_event(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_unknown_causation_boundary"

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run_id),
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_unknown_causation_boundary"},
        )
    )

    with pytest.raises(ValueError, match="causation_id must reference existing event"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(run_id),
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunStarted",
                payload={"run_id": run_id},
                causation_id="event_missing",
            )
        )
