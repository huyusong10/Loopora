from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from run_event_invariant_test_support import append_run_created


def test_strategy_advanced_requires_latest_step_committed_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_strategy_advanced_causation_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    _submitted_event, accepted_event, committed_event = _append_committed_step(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="causation_id to reference latest StepCommitted"):
        _append_strategy_advanced(repository, stream_id, run_id, causation_id=accepted_event.event_id)

    strategy_event = _append_strategy_advanced(repository, stream_id, run_id, causation_id=committed_event.event_id)

    assert strategy_event.payload["step_id"] == "builder"
    with pytest.raises(ValueError, match="already advanced strategy"):
        _append_strategy_advanced(repository, stream_id, run_id, causation_id=committed_event.event_id)


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
