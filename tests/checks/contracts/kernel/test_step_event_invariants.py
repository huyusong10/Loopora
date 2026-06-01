from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef


def test_step_claim_event_requires_pending_actor_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_claim_identity_boundary"
    stream_id = run_stream_id(run_id)
    actor = ActorRef(kind="runner", id="headless")
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="StepClaimed requires pending_actor"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepClaimed",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 1},
                actor=actor,
            )
        )

    event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepClaimed",
            payload={
                "run_id": run_id,
                "step_id": "builder",
                "iteration": 1,
                "pending_actor": actor.to_dict(),
            },
            actor=actor,
        )
    )

    assert event.payload["pending_actor"] == actor.to_dict()


def test_strategy_advanced_requires_latest_step_committed_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_strategy_advanced_causation_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    _submitted_event, accepted_event, committed_event = _append_committed_step(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="causation_id to reference latest StepCommitted"):
        _append_strategy_advanced(repository, stream_id, run_id, causation_id=accepted_event.event_id)

    strategy_event = _append_strategy_advanced(repository, stream_id, run_id, causation_id=committed_event.event_id)

    assert strategy_event.payload["step_id"] == "builder"
    with pytest.raises(ValueError, match="already advanced strategy"):
        _append_strategy_advanced(repository, stream_id, run_id, causation_id=committed_event.event_id)


def test_step_result_events_must_match_causation_step_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_identity_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepSubmitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "status": "completed"},
        )
    )

    with pytest.raises(ValueError, match="step_id to match"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepAccepted",
                payload={"run_id": run_id, "step_id": "inspector", "iteration": 1, "result_status": "completed"},
                causation_id=submitted_event.event_id,
            )
        )
    with pytest.raises(ValueError, match="iteration to match"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepSubmissionRejected",
                payload={"run_id": run_id, "step_id": "builder", "iteration": 2, "reason": "invalid result"},
                causation_id=submitted_event.event_id,
            )
        )


def test_step_result_events_require_step_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_identity_shape_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="requires step_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepSubmitted",
                payload={"run_id": run_id, "iteration": 1, "status": "completed"},
            )
        )
    with pytest.raises(ValueError, match="requires iteration"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="StepSubmitted",
                payload={"run_id": run_id, "step_id": "builder", "status": "completed"},
            )
        )


def test_step_submission_can_only_have_one_accept_or_reject_decision(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_decision_boundary"
    stream_id = run_stream_id(run_id)
    _append_run_created(repository, stream_id, run_id)
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
    _append_run_created(repository, stream_id, run_id)
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


def _append_run_created(repository: LooporaRepository, stream_id: str, run_id: str) -> None:
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_step_claim_identity_boundary"},
        )
    )


def _append_committed_step(repository: LooporaRepository, stream_id: str, run_id: str):
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
    committed_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StepCommitted",
            payload={"run_id": run_id, "step_id": "builder", "iteration": 1, "result_status": "completed"},
            causation_id=accepted_event.event_id,
        )
    )

    return submitted_event, accepted_event, committed_event


def _append_strategy_advanced(
    repository: LooporaRepository,
    stream_id: str,
    run_id: str,
    *,
    causation_id: str,
):
    return repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="StrategyAdvanced",
            payload={
                "run_id": run_id,
                "step_id": "builder",
                "iteration": 1,
                "result_status": "completed",
                "reason": "step_committed",
            },
            causation_id=causation_id,
        )
    )
