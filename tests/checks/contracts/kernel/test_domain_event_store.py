from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id, run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_store_rejects_surface_event_types(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_surface"),
                aggregate_type="run",
                aggregate_id="run_surface",
                event_type="HostTraceObserved",
                payload={"trace": "diagnostic only"},
            )
        )

    assert repository.list_domain_events(run_stream_id("run_surface")) == []


def test_domain_event_transaction_rolls_back_when_later_event_is_rejected(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_atomic_boundary")

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event_transaction(
            lambda event_transaction: (
                event_transaction.append_domain_event(
                    DomainEventAppendRequest(
                        stream_id=stream_id,
                        aggregate_type="run",
                        aggregate_id="run_atomic_boundary",
                        event_type="RunStarted",
                        payload={"run_id": "run_atomic_boundary"},
                    )
                ),
                event_transaction.append_domain_event(
                    DomainEventAppendRequest(
                        stream_id=stream_id,
                        aggregate_type="run",
                        aggregate_id="run_atomic_boundary",
                        event_type="HostTraceObserved",
                        payload={"trace": "diagnostic only"},
                    )
                ),
            )
        )

    assert repository.list_domain_events(stream_id) == []


def test_domain_event_store_exposes_latest_sequence_without_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_latest_sequence")

    assert repository.latest_domain_event_sequence(stream_id) == 0
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_latest_sequence",
            event_type="RunCreated",
            payload={"run_id": "run_latest_sequence", "loop_id": "loop_latest_sequence"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_latest_sequence",
            event_type="RunStarted",
            payload={"run_id": "run_latest_sequence"},
        )
    )

    assert repository.latest_domain_event_sequence(stream_id) == 2


def test_domain_event_transaction_rolls_back_event_derived_artifact_indexes(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_atomic_artifact")

    with pytest.raises(ValueError, match="unsupported core domain event type"):
        repository.append_domain_event_transaction(
            lambda event_transaction: (
                event_transaction.record_artifact_index(
                    {
                        "artifact_id": "artifact_atomic",
                        "run_id": "run_atomic_artifact",
                        "loop_id": "loop_atomic_artifact",
                        "kind": "workspace",
                        "uri": "proof.txt",
                        "created_by_event_id": "event_pending",
                    }
                ),
                event_transaction.append_domain_event(
                    DomainEventAppendRequest(
                        stream_id=stream_id,
                        aggregate_type="run",
                        aggregate_id="run_atomic_artifact",
                        event_type="HostTraceObserved",
                        payload={"trace": "diagnostic only"},
                    )
                ),
            )
        )

    assert repository.list_artifact_index(run_id="run_atomic_artifact") == []
    assert repository.list_domain_events(stream_id) == []


def test_domain_event_store_rejects_aggregate_type_mismatches(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="requires aggregate_type loop"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_wrong_loop_event"),
                aggregate_type="run",
                aggregate_id="run_wrong_loop_event",
                event_type="LoopArchived",
                payload={"loop_id": "loop_wrong"},
            )
        )
    with pytest.raises(ValueError, match="requires aggregate_type run"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id("loop_wrong_run_event"),
                aggregate_type="loop",
                aggregate_id="loop_wrong_run_event",
                event_type="RunStarted",
                payload={"run_id": "run_wrong"},
            )
        )

    assert repository.list_domain_events(run_stream_id("run_wrong_loop_event")) == []
    assert repository.list_domain_events(loop_stream_id("loop_wrong_run_event")) == []
