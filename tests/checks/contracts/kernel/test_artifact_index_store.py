from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_transaction_rolls_back_event_derived_artifact_indexes(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_atomic_artifact")

    def append_artifact_then_rejected_event(event_transaction) -> None:
        source_event = event_transaction.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_atomic_artifact",
                event_type="RunCreated",
                payload={"run_id": "run_atomic_artifact", "loop_id": "loop_atomic_artifact"},
            )
        )
        event_transaction.record_artifact_index(
            {
                "artifact_id": "artifact_atomic",
                "run_id": "run_atomic_artifact",
                "loop_id": "loop_atomic_artifact",
                "kind": "workspace",
                "uri": "proof.txt",
                "created_by_event_id": source_event.event_id,
            }
        )
        event_transaction.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_atomic_artifact",
                event_type="HostTraceObserved",
                payload={"trace": "diagnostic only"},
            )
        )

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event_transaction(append_artifact_then_rejected_event)

    assert repository.list_artifact_index(run_id="run_atomic_artifact") == []
    assert repository.list_domain_events(stream_id) == []


def test_artifact_index_requires_existing_domain_event_source(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="created_by_event_id"):
        repository.record_artifact_index(
            {
                "artifact_id": "artifact_orphan",
                "run_id": "run_orphan",
                "loop_id": "loop_orphan",
                "kind": "workspace",
                "uri": "proof.txt",
            }
        )

    with pytest.raises(ValueError, match="event_store event"):
        repository.record_artifact_index(
            {
                "artifact_id": "artifact_unknown_source",
                "run_id": "run_orphan",
                "loop_id": "loop_orphan",
                "kind": "workspace",
                "uri": "proof.txt",
                "created_by_event_id": "event_missing",
            }
        )

    assert repository.list_artifact_index(run_id="run_orphan") == []
