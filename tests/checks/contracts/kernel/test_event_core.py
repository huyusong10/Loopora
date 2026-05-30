from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.db_run_state_records import RunUpdate
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineAcceptEvidenceRequest,
    RunEngineAdvanceStatus,
    RunEngineClaimStepRequest,
    RunEngineClaimWorkflowStepRequest,
    RunEngineCommitStepRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineCompleteIterationRequest,
    RunEngineIssueVerdictRequest,
    RunEngineRecordStepEvidenceRequest,
    RunEngineStartIterationRequest,
    RunEngineSubmitStepRequest,
    WorkflowStepInstructionRequest,
    workflow_step_instruction,
)
from loopora.events import loop_stream_id, replay_run_snapshot, run_stream_id
from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import ActorRef, ArtifactRef, RunLifecycleStatus, StepResult, StepResultStatus, VerdictStatus


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_markdown = "# Task\n\nProve it.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": "loop_event_core",
            "name": "Event Core Loop",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove it.", "checks": [{"id": "proof", "title": "Proof"}]},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )
    run_dir = workdir / ".loopora" / "runs" / "run_event_core"
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": "run_event_core",
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove it.", "checks": [{"id": "proof", "title": "Proof"}]},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
            "status": "queued",
            "runs_dir": str(run_dir),
        }
    )


def test_run_creation_and_status_updates_are_replayable_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    created_cache = repository.get_projection_record("run_snapshot", run["id"])

    repository.update_run(run["id"], RunUpdate(status="running", started_at="2026-01-01T00:00:00+00:00"))
    repository.update_run(run["id"], RunUpdate(status="succeeded", finished_at="2026-01-01T00:01:00+00:00"))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)
    engine_snapshot = RepositoryRunEngine(repository).snapshot(run["id"])

    assert [event.event_type for event in events] == ["RunCreated", "RunStarted", "RunClosed"]
    assert [event.sequence for event in events] == [1, 2, 3]
    assert snapshot.state.id == run["id"]
    assert snapshot.state.loop_id == run["loop_id"]
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.CLOSED
    assert engine_snapshot.state.lifecycle_status == RunLifecycleStatus.CLOSED
    assert created_cache["source_sequence"] == 1
    assert created_cache["payload"]["lifecycle_status"] == "created"
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])
    assert cached_snapshot["source_sequence"] == 3
    assert cached_snapshot["payload"]["lifecycle_status"] == "closed"


def test_run_lifecycle_events_ignore_repeated_status_updates(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    repository.update_run(run["id"], RunUpdate(status="running", started_at="2026-01-01T00:00:00+00:00"))
    repository.update_run(run["id"], RunUpdate(status="running", current_iter=1, active_role="builder"))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert [event.event_type for event in events] == ["RunCreated", "RunStarted"]
    assert cached_snapshot["source_sequence"] == 2
    assert cached_snapshot["payload"]["lifecycle_status"] == "running"


def test_run_lifecycle_events_distinguish_resume_from_initial_start(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    repository.update_run(run["id"], RunUpdate(status="awaiting_agent", current_iter=1, active_role="builder"))
    repository.update_run(run["id"], RunUpdate(status="running", active_role=""))

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert [event.event_type for event in events] == ["RunCreated", "RunPausedForActor", "RunResumed"]
    assert snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert snapshot.state.pending_actor is None
    assert cached_snapshot["source_sequence"] == 3
    assert cached_snapshot["payload"]["lifecycle_status"] == "running"


def test_projection_store_records_replay_source_sequence(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    record = repository.put_projection_record(
        "run_snapshot",
        "run_projection",
        source_sequence=7,
        payload={"status": "closed"},
    )

    assert record["projection_name"] == "run_snapshot"
    assert record["projection_key"] == "run_projection"
    assert record["source_sequence"] == 7
    assert record["payload"] == {"status": "closed"}


def test_loop_creation_emits_compiler_and_activation_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nProve loop events.\n", encoding="utf-8")

    repository.create_loop(
        {
            "id": "loop_event_stream",
            "name": "Loop Event Stream",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {
                "goal": "Prove loop events.",
                "checks": [{"id": "proof", "title": "Proof"}],
                "coverage_targets": [{"id": "done_when.proof"}],
            },
            "workflow": {
                "roles": [{"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"}],
                "steps": [
                    {
                        "id": "judge",
                        "role_id": "gatekeeper",
                        "action_policy": {"can_finish_run": True},
                    }
                ],
            },
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )

    events = repository.list_domain_events(loop_stream_id("loop_event_stream"))

    assert [event.event_type for event in events] == ["LoopContractCompiled", "LoopStrategyCompiled", "LoopActivated"]
    assert [event.sequence for event in events] == [1, 2, 3]
    assert events[0].payload == {
        "loop_id": "loop_event_stream",
        "name": "Loop Event Stream",
        "task": "Prove loop events.",
        "completion_mode": "gatekeeper",
        "check_count": 1,
        "coverage_target_count": 2,
        "reason": "created",
    }
    assert events[1].payload["finish_step_ids"] == ["judge"]
    assert events[1].causation_id == events[0].event_id
    assert events[2].causation_id == events[1].event_id


def test_loop_contract_updates_emit_compiler_domain_events_without_reactivation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nInitial.\n", encoding="utf-8")
    repository.create_loop(
        {
            "id": "loop_update_events",
            "name": "Loop Update Events",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {"goal": "Initial.", "checks": []},
            "workflow": {"roles": [], "steps": []},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 3,
            "max_role_retries": 2,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )

    updated_spec_path = tmp_path / "updated.md"
    updated_spec_path.write_text("# Task\n\nUpdated.\n", encoding="utf-8")
    repository.update_loop_contract(
        "loop_update_events",
        {
            "spec_path": str(updated_spec_path),
            "spec_markdown": updated_spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {
                "goal": "Updated.",
                "checks": [{"id": "updated", "title": "Updated"}],
                "coverage_targets": [{"id": "done_when.updated"}],
            },
            "workflow": {
                "roles": [{"id": "builder", "name": "Builder", "archetype": "builder"}],
                "steps": [{"id": "build", "role_id": "builder"}],
            },
        },
    )

    events = repository.list_domain_events(loop_stream_id("loop_update_events"))

    assert [event.event_type for event in events] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopContractCompiled",
        "LoopStrategyCompiled",
    ]
    assert events[-2].payload["task"] == "Updated."
    assert events[-2].payload["name"] == "Loop Update Events"
    assert events[-2].payload["coverage_target_count"] == 2
    assert events[-2].payload["reason"] == "updated"
    assert events[-1].payload["role_count"] == 1
    assert events[-1].payload["max_iterations"] == 3
    assert events[-1].payload["max_step_retries"] == 2
    assert events[-1].causation_id == events[-2].event_id
    cached = repository.get_projection_record("loop_definition", "loop_update_events")
    assert cached["source_sequence"] == 5
    assert cached["payload"]["name"] == "Loop Update Events"
    assert cached["payload"]["task"] == "Updated."
    assert cached["payload"]["step_count"] == 1


def test_loop_delete_archives_loop_stream_before_removing_legacy_record(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nArchive me.\n", encoding="utf-8")
    repository.create_loop(
        {
            "id": "loop_archive_event",
            "name": "Loop Archive Event",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {"goal": "Archive me.", "checks": []},
            "workflow": {"roles": [], "steps": []},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )

    assert repository.delete_loop("loop_archive_event") is True
    assert repository.get_loop("loop_archive_event") is None
    events = repository.list_domain_events(loop_stream_id("loop_archive_event"))

    assert [event.event_type for event in events] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopArchived",
    ]
    assert events[-1].payload == {"loop_id": "loop_archive_event", "reason": "deleted"}
    cached = repository.get_projection_record("loop_definition", "loop_archive_event")
    assert cached["source_sequence"] == 4
    assert cached["payload"]["status"] == "archived"


def test_run_engine_start_moves_created_run_to_ready_for_step(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    outcome = RepositoryRunEngine(repository).start(run["id"])
    events = repository.list_domain_events(run_stream_id(run["id"]))

    assert outcome.status == RunEngineAdvanceStatus.READY_FOR_STEP
    assert outcome.next_action == "claim_step"
    assert outcome.snapshot.state.lifecycle_status == RunLifecycleStatus.RUNNING
    assert [event.event_type for event in events] == ["RunCreated", "RunStarted"]


def test_run_engine_advance_closes_passing_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.start(run["id"])
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Evidence is enough."},
        )
    )

    outcome = engine.advance(run["id"])
    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_snapshot = repository.get_projection_record("run_snapshot", run["id"])

    assert outcome.status == RunEngineAdvanceStatus.CLOSED
    assert outcome.next_action == "complete"
    assert outcome.verdict_status.value == "passed"
    assert events[-1].event_type == "RunClosed"
    assert cached_snapshot["payload"]["lifecycle_status"] == "closed"


def test_run_engine_advance_preserves_awaiting_actor_state(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    instruction = workflow_step_instruction(
        WorkflowStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )

    engine.start(run["id"])
    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))

    outcome = engine.advance(run["id"])

    assert outcome.status == RunEngineAdvanceStatus.AWAITING_ACTOR
    assert outcome.next_action == "await_actor_submit"
    assert outcome.current_step_id == "builder"
    assert outcome.pending_actor == actor


def test_terminal_run_event_clears_pending_current_step(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=workflow_step_instruction(
                WorkflowStepInstructionRequest(
                    run_id=run["id"],
                    contract_ref="contract/run_contract.json",
                    compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
                    iteration=1,
                    step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
                    role={"id": "builder", "name": "Builder", "archetype": "builder"},
                )
            ),
            pending_actor=actor,
        )
    )
    repository.update_run(run["id"], RunUpdate(status="failed", finished_at="2026-01-01T00:01:00+00:00"))

    snapshot = replay_run_snapshot(repository.list_domain_events(run_stream_id(run["id"])))
    current_step = replay_run_projections(repository, run["id"])["current_step"]

    assert snapshot.state.lifecycle_status == RunLifecycleStatus.FAILED
    assert snapshot.state.current_step_id is None
    assert snapshot.state.pending_actor is None
    assert current_step["step_id"] is None
    assert current_step["claimable"] is False


def test_run_engine_step_instruction_events_drive_current_step_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    instruction = workflow_step_instruction(
        WorkflowStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )

    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))

    claimed = engine.snapshot(run["id"])
    assert claimed.state.lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR
    assert claimed.state.current_step_id == "builder"
    assert claimed.state.current_iteration == 1
    assert claimed.state.pending_actor == actor

    engine.commit_step(
        RunEngineCommitStepRequest(
            run_id=run["id"],
            step_id="builder",
            iteration=1,
            actor=actor,
        )
    )

    committed = engine.snapshot(run["id"])
    assert committed.state.current_step_id is None
    assert committed.state.pending_actor is None


def test_run_engine_claim_workflow_step_freezes_step_instruction(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    claimed = engine.claim_workflow_step(
        RunEngineClaimWorkflowStepRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
            pending_actor=actor,
        )
    )

    event = repository.list_domain_events(run_stream_id(run["id"]))[-1]

    assert claimed.instruction.step_id == "builder"
    assert claimed.instruction.evidence_scope.target_ids == ("done_when.proof",)
    assert event.event_type == "StepInstructionIssued"
    assert event.payload["step_id"] == claimed.instruction.step_id
    assert event.payload["pending_actor"] == actor.to_dict()


def test_run_engine_derives_workflow_cursor_from_event_log(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run["id"],
                step_id="builder",
                iteration=0,
                actor=actor,
                status=StepResultStatus.COMPLETED,
                summary="Builder completed.",
            )
        )
    )

    step_index = engine.workflow_step_index(
        run["id"],
        workflow_steps=[
            {"id": "builder", "role_id": "builder"},
            {"id": "gatekeeper", "role_id": "gatekeeper"},
        ],
        iteration=0,
        fallback_step_index=0,
    )

    assert step_index == 1


def test_run_engine_records_iteration_lifecycle_events_idempotently(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.start_iteration(RunEngineStartIterationRequest(run_id=run["id"], iteration=0, actor=actor, step_count=2))
    engine.start_iteration(RunEngineStartIterationRequest(run_id=run["id"], iteration=0, actor=actor, step_count=2))
    engine.complete_iteration(
        RunEngineCompleteIterationRequest(
            run_id=run["id"],
            iteration=0,
            actor=actor,
            completed_step_count=2,
            reason="checkpointed",
        )
    )
    engine.complete_iteration(
        RunEngineCompleteIterationRequest(
            run_id=run["id"],
            iteration=0,
            actor=actor,
            completed_step_count=2,
            reason="checkpointed",
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    snapshot = replay_run_snapshot(events)

    assert [event.event_type for event in events] == ["RunCreated", "IterationStarted", "IterationCompleted"]
    assert snapshot.state.current_iteration == 0
    assert events[-1].payload["completed_step_count"] == 2


def test_run_engine_submit_step_records_submitted_and_committed_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    result = engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run["id"],
                step_id="builder",
                iteration=1,
                actor=actor,
                status=StepResultStatus.COMPLETED,
                summary="Builder completed the proof.",
                artifact_refs=(ArtifactRef(kind="workspace", label="report", uri="report.txt", content_hash="sha256:abc"),),
                blocking_items=("none",),
            )
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    artifacts = repository.list_artifact_index(run_id=run["id"])

    assert result.submitted_event.event_type == "StepSubmitted"
    assert result.committed_event.event_type == "StepCommitted"
    assert [item.event_type for item in events[-2:]] == ["StepSubmitted", "StepCommitted"]
    assert events[-2].payload["summary"] == "Builder completed the proof."
    assert result.committed_event.causation_id == result.submitted_event.event_id
    assert events[-1].event_id == result.committed_event.event_id
    assert artifacts[0]["loop_id"] == run["loop_id"]
    assert artifacts[0]["kind"] == "workspace"
    assert artifacts[0]["uri"] == "report.txt"
    assert artifacts[0]["content_hash"] == "sha256:abc"
    assert artifacts[0]["created_by_event_id"] == result.submitted_event.event_id


def test_run_engine_records_evidence_coverage_and_verdict_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

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
                "artifact_refs": [{"kind": "workspace"}],
            },
        )
    )
    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection={
                "status": "covered",
                "target_count": 1,
                "covered_target_count": 1,
                "top_gaps": [],
            },
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

    assert [event.event_type for event in events[-3:]] == ["EvidenceAccepted", "CoverageRecomputed", "VerdictIssued"]
    assert events[-3].payload["evidence_id"] == "ev_001"
    assert events[-2].payload["covered_target_count"] == 1
    assert replay_run_snapshot(events).verdict_status.value == "passed"


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
    run = _create_run(repository, tmp_path)

    RepositoryRunEngine(repository).issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=ActorRef(kind="runner", id="headless"),
            verdict={"status": legacy_status, "source": "gatekeeper", "summary": "Legacy verdict status."},
        )
    )

    snapshot = replay_run_snapshot(repository.list_domain_events(run_stream_id(run["id"])))

    assert snapshot.verdict_status == kernel_status


def test_run_engine_records_step_evidence_and_coverage_as_one_command(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    result = engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            correlation_id="corr-step-evidence",
            evidence_entry={
                "id": "ev_step_001",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Step proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
                "artifact_refs": [{"kind": "workspace"}],
            },
            coverage_projection={
                "status": "covered",
                "target_count": 1,
                "covered_target_count": 1,
                "top_gaps": [],
            },
        )
    )

    events = repository.list_domain_events(run_stream_id(run["id"]))
    cached_ledger = repository.get_projection_record("evidence_ledger", run["id"])
    cached_coverage = repository.get_projection_record("coverage", run["id"])

    assert [event.event_type for event in events[-2:]] == ["EvidenceAccepted", "CoverageRecomputed"]
    assert result.evidence_event.event_id == events[-2].event_id
    assert result.coverage_event.event_id == events[-1].event_id
    assert events[-2].correlation_id == "corr-step-evidence"
    assert events[-1].correlation_id == "corr-step-evidence"
    assert events[-1].causation_id == events[-2].event_id
    assert cached_ledger["payload"]["entries"][0]["evidence_id"] == "ev_step_001"
    assert cached_coverage["payload"]["status"] == "covered"
    assert cached_coverage["payload"]["source_sequence"] == events[-1].sequence


def test_run_engine_record_step_evidence_does_not_leave_half_events_on_invalid_coverage(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    with pytest.raises(ValueError):
        engine.record_step_evidence(
            RunEngineRecordStepEvidenceRequest(
                run_id=run["id"],
                actor=ActorRef(kind="runner", id="headless"),
                evidence_entry={
                    "id": "ev_half_write",
                    "step_id": "builder",
                    "role_id": "builder",
                    "claim": "This evidence should not persist alone.",
                },
                coverage_projection={"status": "covered", "target_count": "not-a-number"},
            )
        )

    events = repository.list_domain_events(run_stream_id(run["id"]))

    assert [event.event_type for event in events] == ["RunCreated"]
