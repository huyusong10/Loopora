from __future__ import annotations

# Merged from kernel/test_run_event_verdict_status_invariants.py
from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id
from loopora.events.run_event_payloads import verdict_issued_payload
from loopora.events.store import DomainEventAppendRequest

from run_event_invariant_test_support import append_run_created


def test_verdict_status_must_be_kernel_verdict_status(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_status_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="kernel verdict status"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="VerdictIssued",
                payload={"run_id": run_id, "status": "failed"},
            )
        )


@pytest.mark.parametrize(
    ("legacy_status", "kernel_status"),
    [
        ("insufficient_evidence", "continue_required"),
        ("failed", "blocked"),
    ],
)
def test_verdict_payload_normalizes_legacy_statuses_before_append(
    tmp_path: Path,
    legacy_status: str,
    kernel_status: str,
) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = f"run_legacy_verdict_status_{kernel_status}"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload=verdict_issued_payload(run_id, {"status": legacy_status}),
        )
    )

    assert verdict_event.payload["status"] == kernel_status

# Merged from kernel/test_runner_parity.py

from loopora.runners import agent_runner_actor, headless_runner_actor

from runner_parity_test_support import run_submission_flow


def test_headless_and_agent_runner_submissions_replay_to_same_domain_outputs(tmp_path: Path) -> None:
    headless = run_submission_flow(
        tmp_path,
        actor=headless_runner_actor(),
        run_id="run_runner_parity_headless",
        loop_id="loop_runner_parity_headless",
    )
    agent = run_submission_flow(
        tmp_path,
        actor=agent_runner_actor("codex"),
        run_id="run_runner_parity_agent",
        loop_id="loop_runner_parity_agent",
    )

    assert agent == headless

# Merged from kernel/test_step_claim_event_invariants.py

import pytest

from loopora.kernel import ActorRef


def test_step_claim_event_requires_pending_actor_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_claim_identity_boundary"
    stream_id = run_stream_id(run_id)
    actor = ActorRef(kind="runner", id="headless")
    append_run_created(repository, stream_id, run_id)

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

# Merged from kernel/test_step_result_event_identity_invariants.py

import pytest



def test_step_result_events_must_match_causation_step_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_step_result_identity_boundary"
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
    append_run_created(repository, stream_id, run_id)

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

# Merged from kernel/test_verdict_engine_coverage_parity.py

from loopora.kernel import VerdictStatus

from verdict_engine_parity_test_support import (
    LEGACY_TO_KERNEL_STATUS,
    base_compiled_spec,
    coverage_payload,
    legacy_and_kernel_statuses,
    refund_targets,
)


def test_verdict_engine_matches_legacy_for_missing_required_evidence(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec()
    coverage = coverage_payload(refund_targets(permission_status="missing"))

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_matches_legacy_for_blocking_coverage(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec()
    coverage = coverage_payload(refund_targets(fake_done_status="blocked"))

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.BLOCKED

# Merged from kernel/test_verdict_requires_coverage_causation_store.py

import pytest


from run_event_invariant_test_support import append_coverage_recomputed, append_verdict_issued


def test_domain_event_store_requires_verdict_causation_when_coverage_exists(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_causation_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_verdict_causation_boundary")

    coverage_event = append_coverage_recomputed(
        repository,
        stream_id,
        run_id,
        payload={"status": "partial", "target_count": 1, "missing_target_count": 1},
    )
    with pytest.raises(ValueError, match="VerdictIssued requires causation_id"):
        append_verdict_issued(repository, stream_id, run_id, payload={"status": "continue_required"})

    verdict_event = append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={"status": "continue_required"},
        causation_id=coverage_event.event_id,
    )
    assert verdict_event.causation_id == coverage_event.event_id

    requested_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictRequested",
            payload={"run_id": run_id, "requested_status": "continue_required"},
            causation_id=coverage_event.event_id,
        )
    )
    issued_event = append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={"status": "continue_required"},
        causation_id=requested_event.event_id,
    )

    assert issued_event.causation_id == requested_event.event_id
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "CoverageRecomputed",
        "VerdictIssued",
        "VerdictRequested",
        "VerdictIssued",
    ]
