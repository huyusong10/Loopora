from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_domain_event_store_rejects_step_result_events_without_causation_chain(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_step_result_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires prior StepAccepted"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepCommitted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "status": "completed"},
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepSubmissionRejected",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "reason": "invalid result"},
            )
        )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepAccepted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    accepted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepAccepted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            causation_id=submitted_event.event_id,
        )
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepCommitted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            )
        )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepCommitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            causation_id=accepted_event.event_id,
        )
    )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "StepSubmitted",
        "StepAccepted",
        "StepCommitted",
    ]
