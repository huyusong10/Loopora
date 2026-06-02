from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from run_event_invariant_test_support import append_run_created


def test_step_submission_can_only_have_one_accept_or_reject_decision(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_decision_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "status": "completed"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmissionRejected",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "reason": "invalid result"},
            causation_id=submitted_event.event_id,
        )
    )

    with pytest.raises(ValueError, match="already has accepted or rejected decision"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepAccepted",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
                causation_id=submitted_event.event_id,
            )
        )


def test_step_acceptance_can_only_be_committed_once(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_commit_decision_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "status": "completed"},
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

    with pytest.raises(ValueError, match="already has committed result"):
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
