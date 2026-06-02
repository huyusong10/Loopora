from __future__ import annotations

# Merged from kernel/test_passing_verdict_requires_passable_coverage_store.py
from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import run_stream_id

from run_event_invariant_test_support import (
    append_accepted_evidence,
    append_coverage_recomputed,
    append_run_created,
    append_verdict_issued,
)


def test_domain_event_store_rejects_passing_verdict_without_passable_coverage(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_verdict_coverage_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_verdict_coverage_boundary")

    with pytest.raises(ValueError, match="requires latest CoverageRecomputed"):
        append_verdict_issued(repository, stream_id, run_id, payload={"status": "passed"})

    partial_coverage_event = append_coverage_recomputed(
        repository,
        stream_id,
        run_id,
        payload={"status": "partial", "target_count": 1, "missing_target_count": 1},
    )
    with pytest.raises(ValueError, match="VerdictIssued requires causation_id"):
        append_verdict_issued(repository, stream_id, run_id, payload={"status": "passed_with_residual_risk"})
    with pytest.raises(ValueError, match="requires latest CoverageRecomputed"):
        append_verdict_issued(
            repository,
            stream_id,
            run_id,
            payload={"status": "passed_with_residual_risk"},
            causation_id=partial_coverage_event.event_id,
        )

    evidence_event = append_accepted_evidence(
        repository,
        stream_id,
        run_id,
        evidence_id="ev_verdict_coverage",
        verifies=["target:done_when.proof:weak"],
    )
    coverage_event = append_coverage_recomputed(
        repository,
        stream_id,
        run_id,
        payload={"status": "weak", "target_count": 2, "covered_target_count": 1, "weak_target_count": 1},
        causation_id=evidence_event.event_id,
    )
    with pytest.raises(ValueError, match="requires causation_id"):
        append_verdict_issued(repository, stream_id, run_id, payload={"status": "passed_with_residual_risk"})

    append_verdict_issued(
        repository,
        stream_id,
        run_id,
        payload={
            "status": "passed_with_residual_risk",
            "buckets": {"residual_risk": [{"label": "Manual follow-up remains.", "managed": True}]},
        },
        causation_id=coverage_event.event_id,
    )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "CoverageRecomputed",
        "EvidenceAccepted",
        "CoverageRecomputed",
        "VerdictIssued",
    ]

# Merged from kernel/test_projection_store_repository_architecture.py
from kernel_architecture_test_support import design_contracts_source, loopora_source


def test_domain_event_repository_delegates_projection_store_records() -> None:
    db_event_source = loopora_source("db_domain_event_records.py")
    projection_source = loopora_source("db_projection_records.py")
    runtime_state_source = loopora_source("db_runtime_state.py")
    contracts_source = design_contracts_source()

    assert "from loopora.db_projection_records import RepositoryProjectionRecordsMixin" in runtime_state_source
    assert "RepositoryProjectionRecordsMixin" in runtime_state_source
    assert "class RepositoryProjectionRecordsMixin" in projection_source
    assert "def get_projection_record" in projection_source
    assert "def put_projection_record_for_connection" in projection_source
    assert "projection_store" in projection_source
    assert "projection_store" not in db_event_source
    assert "get_projection_record" not in db_event_source
    assert "db_projection_records.py" in contracts_source

# Merged from kernel/test_residual_risk_acceptance_event_causation.py



from run_event_invariant_test_support import (
    append_residual_risk_accepted,
    append_residual_risk_verdict,
    append_verdict_allowed_closure,
)


def test_residual_risk_accepted_requires_allowed_closure_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_residual_risk_acceptance_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id, loop_id="loop_residual_risk_acceptance_boundary")
    verdict_event = append_residual_risk_verdict(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="requires prior VerdictAllowedClosure"):
        append_residual_risk_accepted(repository, stream_id, run_id, causation_id=verdict_event.event_id)

    closure_event = append_verdict_allowed_closure(
        repository,
        stream_id,
        run_id,
        causation_id=verdict_event.event_id,
    )
    residual_event = append_residual_risk_accepted(
        repository,
        stream_id,
        run_id,
        causation_id=closure_event.event_id,
    )

    assert residual_event.payload["risk_count"] == 1
    with pytest.raises(ValueError, match="already accepted residual risk"):
        append_residual_risk_accepted(repository, stream_id, run_id, causation_id=closure_event.event_id)

# Merged from kernel/test_run_engine_awaiting_actor_replay.py

from loopora.db_run_state_records import RunUpdate
from loopora.engine import RepositoryRunEngine, RunEngineAdvanceStatus
from loopora.events import replay_run_snapshot
from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import RunLifecycleStatus

from run_engine_lifecycle_replay_test_support import claim_builder_step, create_lifecycle_replay_run


def test_run_engine_advance_preserves_awaiting_actor_state(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_lifecycle_replay_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    engine.start(run["id"])
    actor = claim_builder_step(engine, run["id"])
    outcome = engine.advance(run["id"])

    assert outcome.status == RunEngineAdvanceStatus.AWAITING_ACTOR
    assert outcome.next_action == "await_actor_submit"
    assert outcome.current_step_id == "builder"
    assert outcome.pending_actor == actor


def test_terminal_run_event_clears_pending_current_step(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_lifecycle_replay_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    claim_builder_step(engine, run["id"])
    repository.update_run(run["id"], RunUpdate(status="failed", finished_at="2026-01-01T00:01:00+00:00"))

    snapshot = replay_run_snapshot(repository.list_domain_events(run_stream_id(run["id"])))
    current_step = replay_run_projections(repository, run["id"])["current_step"]

    assert snapshot.state.lifecycle_status == RunLifecycleStatus.FAILED
    assert snapshot.state.current_step_id is None
    assert snapshot.state.pending_actor is None
    assert current_step["step_id"] is None
    assert current_step["claimable"] is False

# Merged from kernel/test_run_engine_evidence_chain_events.py

from loopora.engine import (
    RunEngineAcceptEvidenceRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueVerdictRequest,
)

from run_engine_evidence_event_test_support import (
    covered_projection,
    create_run_engine_evidence_run,
    headless_runner_actor,
)


def test_run_engine_records_evidence_coverage_and_verdict_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_run_engine_evidence_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = headless_runner_actor()

    engine.accept_evidence(
        RunEngineAcceptEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_001",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
                "artifact_refs": [{"kind": "workspace", "label": "proof", "uri": "evidence.txt"}],
            },
        )
    )
    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection=covered_projection(),
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Evidence is enough."},
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    artifacts = repository.list_artifact_index(run_id=run["id"])

    assert [event.event_type for event in events[-5:]] == [
        "EvidenceAccepted",
        "CoverageRecomputed",
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
    ]
    assert events[-5].payload["evidence_id"] == "ev_001"
    assert events[-4].causation_id == events[-5].event_id
    assert events[-3].causation_id == events[-4].event_id
    assert events[-2].causation_id == events[-3].event_id
    assert events[-1].causation_id == events[-2].event_id
    assert artifacts[0]["uri"] == "evidence.txt"
    assert artifacts[0]["created_by_event_id"] == events[-5].event_id
    assert events[-4].payload["covered_target_count"] == 1
    assert replay_run_snapshot(events).verdict_status.value == "passed"

# Merged from kernel/test_run_engine_legacy_verdict_replay.py


from loopora.kernel import VerdictStatus



@pytest.mark.parametrize(
    ("legacy_status", "kernel_status"),
    [
        ("insufficient_evidence", VerdictStatus.CONTINUE_REQUIRED),
        ("failed", VerdictStatus.BLOCKED),
    ],
)
def test_event_replay_maps_legacy_task_verdict_statuses_to_kernel_statuses(
    tmp_path: Path,
    legacy_status: str,
    kernel_status: VerdictStatus,
) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_run_engine_evidence_run(repository, tmp_path)

    RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=headless_runner_actor(),
            verdict={"status": legacy_status, "source": "gatekeeper", "summary": "Legacy verdict status."},
        )
    )

    assert replay_run_snapshot(repository.list_domain_events(run_stream_id(run["id"]))).verdict_status == kernel_status

# Merged from kernel/test_run_engine_lifecycle_architecture.py
from kernel_architecture_test_support import REPO_ROOT


def test_run_engine_uses_public_event_store_boundary_for_atomic_writes() -> None:
    source = loopora_source("engine/run_engine.py")

    assert "._append_domain_event_for_connection" not in source


def test_run_engine_delegates_legacy_lifecycle_state_updates() -> None:
    engine_source = loopora_source("engine/run_engine.py")
    lifecycle_commands_source = loopora_source("engine/run_lifecycle_commands.py")
    lifecycle_updates_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_lifecycle_updates.py"
    legacy_updates_source = loopora_source("engine/run_legacy_updates.py")

    assert "update_run(" not in engine_source
    assert "utc_now" not in engine_source
    assert "RunLifecycleStatus" not in engine_source
    assert "VerdictStatus" not in engine_source
    assert "mark_run_started" not in engine_source
    assert "mark_run_succeeded" not in engine_source
    assert "start_run" in engine_source
    assert "advance_run" in engine_source
    assert not lifecycle_updates_path.exists()
    assert "from loopora.engine.run_legacy_updates import mark_run_started, mark_run_succeeded" in lifecycle_commands_source
    assert "mark_run_started" in lifecycle_commands_source
    assert "mark_run_succeeded" in lifecycle_commands_source
    assert "RunLifecycleStatus" in lifecycle_commands_source
    assert "VerdictStatus" in lifecycle_commands_source
    assert "update_run(" in legacy_updates_source
    assert 'status="running"' in legacy_updates_source
    assert 'status="succeeded"' in legacy_updates_source


def test_run_snapshot_legacy_row_adapter_is_separate_from_lifecycle_outcomes() -> None:
    lifecycle_source = loopora_source("engine/run_lifecycle.py")
    legacy_source = loopora_source("engine/run_legacy_snapshot.py")
    snapshot_source = loopora_source("engine/run_snapshot_source.py")

    assert "legacy_run_snapshot" not in lifecycle_source
    assert "legacy_status_to_lifecycle" not in lifecycle_source
    assert "def legacy_run_snapshot" in legacy_source
    assert "lifecycle_status_from_public_run_status" in legacy_source
    assert "def legacy_status_to_lifecycle" not in legacy_source
    assert "from loopora.engine.run_legacy_snapshot import legacy_run_snapshot, missing_run_snapshot" in snapshot_source

# Merged from kernel/test_run_engine_lifecycle_start_replay.py




def test_run_engine_start_moves_created_run_to_ready_for_step(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_lifecycle_replay_run(repository, tmp_path)

    outcome = RepositoryRunEngine(repository).start(run["id"])
    events = repository.list_domain_events(run_stream_id(run["id"]))

    assert outcome.status == RunEngineAdvanceStatus.READY_FOR_STEP
    assert outcome.next_action == "claim_step"
    assert outcome.snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert [event.event_type for event in events] == ["RunCreated", "RunStarted"]

# Merged from kernel/test_run_engine_step_claims.py

from loopora.engine import (
    RunEngineClaimRunnerStepRequest,
    RunEngineClaimStepRequest,
    runner_step_instruction,
)
from loopora.kernel import ActorRef

from run_engine_step_submission_test_support import create_step_submission_run, step_submission_instruction


def test_run_engine_claim_runner_step_freezes_step_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    claimed = engine.claim_runner_step(
        RunEngineClaimRunnerStepRequest(
            instruction=runner_step_instruction(step_submission_instruction(run["id"])),
            pending_actor=actor,
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    planned_event = events[-3]
    claimed_event = events[-2]
    event = events[-1]

    assert claimed.instruction.step_id == "builder"
    assert claimed.instruction.evidence_scope.target_ids == ("done_when.proof",)
    assert planned_event.event_type == "StepPlanned"
    assert planned_event.payload == {"run_id": run["id"], "step_id": "builder", "iteration": 1}
    assert claimed_event.event_type == "StepClaimed"
    assert claimed_event.causation_id == planned_event.event_id
    assert claimed_event.payload == {
        "run_id": run["id"],
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": actor.to_dict(),
    }
    assert event.event_type == "StepInstructionIssued"
    assert event.causation_id == claimed_event.event_id
    assert event.payload["step_id"] == claimed.instruction.step_id
    assert event.payload["pending_actor"] == actor.to_dict()


def test_run_engine_claim_step_returns_step_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_step_submission_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    instruction = runner_step_instruction(step_submission_instruction(run["id"]))

    claimed = engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=instruction,
            pending_actor=actor,
        )
    )

    assert claimed == instruction
    assert repository.list_domain_events(run_stream_id(run["id"]))[-1].event_type == "StepInstructionIssued"

# Merged from kernel/test_run_engine_step_evidence_rollback.py

import pytest

from loopora.engine import RunEngineRecordStepEvidenceRequest



@pytest.mark.parametrize("invalid_count", ["not-a-number", True])
def test_run_engine_record_step_evidence_does_not_leave_half_events_on_invalid_coverage(
    tmp_path: Path,
    invalid_count: object,
) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_run_engine_evidence_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    with pytest.raises(ValueError, match="target_count"):
        engine.record_step_evidence(
            RunEngineRecordStepEvidenceRequest(
                run_id=run["id"],
                actor=headless_runner_actor(),
                evidence_entry={
                    "id": "ev_half_write",
                    "step_id": "builder",
                    "role_id": "builder",
                    "claim": "This evidence should not persist alone.",
                },
                coverage_projection={"status": "covered", "target_count": invalid_count},
            )
        )

    events = repository.list_domain_events(run_stream_id(run["id"]))

    assert [event.event_type for event in events] == ["RunCreated"]

# Merged from kernel/test_run_event_coverage_count_invariants.py

import pytest

from loopora.events.store import DomainEventAppendRequest



def test_coverage_classified_target_counts_cannot_exceed_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_classified_count_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_coverage_counts")

    with pytest.raises(ValueError, match="classified target counts"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={
                    "run_id": run_id,
                    "status": "weak",
                    "target_count": 2,
                    "covered_target_count": 1,
                    "weak_target_count": 1,
                    "missing_target_count": 1,
                },
                causation_id=evidence_event.event_id,
            )
        )


def test_blocked_coverage_requires_blocked_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_blocked_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="blocked_target_count"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "blocked", "target_count": 1},
            )
        )


def test_weak_coverage_requires_weak_or_missing_target_count(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_weak_coverage_count_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    evidence_event = append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_weak_counts")

    with pytest.raises(ValueError, match="weak or missing targets"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "weak", "target_count": 1, "covered_target_count": 1},
                causation_id=evidence_event.event_id,
            )
        )

# Merged from kernel/test_run_event_evidence_reference_invariants.py

import pytest




def test_accepted_evidence_verified_evidence_refs_must_reference_prior_accepted_evidence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_ref_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="verifies evidence refs must reference prior accepted evidence"):
        append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_bad_link", verifies=["evidence:ev_missing"])
    with pytest.raises(ValueError, match="verifies evidence refs must reference prior accepted evidence"):
        append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_self_claim", verifies=["evidence:ev_self_claim"])
    append_accepted_evidence(repository, stream_id, run_id, evidence_id="ev_base")
    self_measured_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": "ev_self_measured",
                "verifies": ["evidence:ev_self_measured"],
                "measured_evidence": True,
            },
        )
    )
    linked_event = append_accepted_evidence(
        repository,
        stream_id,
        run_id,
        evidence_id="ev_linked",
        verifies=["evidence:ev_base"],
    )

    assert self_measured_event.payload["measured_evidence"] is True
    assert linked_event.sequence == self_measured_event.sequence + 1
    assert linked_event.payload["verifies"] == ["evidence:ev_base"]


def test_accepted_evidence_verifies_must_be_a_list(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_verifies_shape_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)

    with pytest.raises(ValueError, match="verifies must be a list"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "evidence_id": "ev_bad_shape", "verifies": "target:done_when.proof"},
            )
        )

# Merged from kernel/test_run_event_next_gap_selection_invariants.py

import pytest




def test_next_gap_selected_requires_blocked_closure_causation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_next_gap_selected_boundary"
    stream_id = run_stream_id(run_id)
    append_run_created(repository, stream_id, run_id)
    verdict_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictIssued",
            payload={
                "run_id": run_id,
                "status": "continue_required",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
        )
    )
    closure_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="VerdictBlockedClosure",
            payload={"run_id": run_id, "verdict_status": "continue_required", "allowed": False},
            causation_id=verdict_event.event_id,
        )
    )

    with pytest.raises(ValueError, match="causation_id to reference latest VerdictBlockedClosure"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="NextGapSelected",
                payload={
                    "run_id": run_id,
                    "target_id": "done_when.proof",
                    "status": "missing",
                    "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
                },
                causation_id=verdict_event.event_id,
            )
        )

    selected_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="NextGapSelected",
            payload={
                "run_id": run_id,
                "target_id": "done_when.proof",
                "status": "missing",
                "next_gap": [{"target_id": "done_when.proof", "status": "missing"}],
            },
            causation_id=closure_event.event_id,
        )
    )

    assert selected_event.payload["target_id"] == "done_when.proof"
