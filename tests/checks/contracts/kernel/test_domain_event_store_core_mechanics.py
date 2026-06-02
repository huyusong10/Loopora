from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


LATEST_SEQUENCE_AFTER_TWO_APPENDS = 2


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

    assert repository.latest_domain_event_sequence(stream_id) == LATEST_SEQUENCE_AFTER_TWO_APPENDS
