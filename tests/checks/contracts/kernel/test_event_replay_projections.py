from __future__ import annotations

import json
from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineAcceptEvidenceRequest,
    RunEngineClaimStepRequest,
    RunEngineCompleteIterationRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueVerdictRequest,
    RunEngineStartIterationRequest,
    RunnerStepInstructionRequest,
    runner_step_instruction,
)
from loopora.events import loop_stream_id, run_stream_id
from loopora.events.projection_cache import (
    current_step_projection_for_run,
    rebuild_run_projection_cache,
    replay_run_projections,
    run_projection_bundle_for_run,
)
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import ActorRef
from loopora.projections import replay_loop_projection_bundle


def _create_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_markdown = "# Task\n\nProve replay.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": "loop_event_projection",
            "name": "Event Projection Loop",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove replay.", "checks": [{"id": "proof", "title": "Proof"}]},
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
    run_dir = workdir / ".loopora" / "runs" / "run_event_projection"
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": "run_event_projection",
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Prove replay.", "checks": [{"id": "proof", "title": "Proof"}]},
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


def test_run_engine_replays_evidence_coverage_verdict_and_audit_projections(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

    engine.accept_evidence(
        RunEngineAcceptEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_replay",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Replay proof exists.",
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
            verdict={"status": "passed", "source": "gatekeeper", "summary": "Replay says pass."},
        )
    )

    projections = replay_run_projections(repository, run["id"])
    cached_coverage = repository.get_projection_record("coverage", run["id"])
    cached_verdict = repository.get_projection_record("task_verdict", run["id"])

    assert projections["run_snapshot"]["run_id"] == run["id"]
    assert projections["current_step"]["claimable"] is False
    assert projections["evidence_ledger"]["entries"][0]["evidence_id"] == "ev_replay"
    assert projections["evidence_ledger"]["entries"][0]["claim"] == "Replay proof exists."
    assert projections["coverage"]["status"] == "covered"
    assert projections["coverage"]["covered_target_count"] == 1
    assert projections["coverage"]["top_gaps"] == []
    assert projections["task_verdict"] == {
        "schema_version": 1,
        "kind": "event_replayed_task_verdict",
        "source_sequence": 6,
        "status": "passed",
        "source": "gatekeeper",
        "summary": "Replay says pass.",
    }
    assert cached_coverage["source_sequence"] == 6
    assert cached_coverage["payload"]["source_sequence"] == 6
    assert cached_verdict["source_sequence"] == 6
    assert cached_verdict["payload"]["status"] == "passed"
    assert projections["audit_timeline"]["events"][2]["event_type"] == "CoverageRecomputed"
    events = repository.list_domain_events(run_stream_id(run["id"]))
    coverage_event = events[2]
    evidence_event = events[1]
    requested_event = events[3]
    verdict_event = events[4]
    closure_event = events[5]
    assert coverage_event.causation_id == evidence_event.event_id
    assert requested_event.causation_id == coverage_event.event_id
    assert verdict_event.causation_id == requested_event.event_id
    assert closure_event.causation_id == verdict_event.event_id
    assert [event["event_type"] for event in projections["audit_timeline"]["events"]] == [
        "RunCreated",
        "EvidenceAccepted",
        "CoverageRecomputed",
        "VerdictRequested",
        "VerdictIssued",
        "VerdictAllowedClosure",
    ]


def test_run_projection_bundle_prefers_fresh_projection_store_without_rebuild(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)

    def fail_rebuild(_run_id: str) -> dict:
        raise AssertionError("fresh projection_store records should be used without rebuilding")

    monkeypatch.setattr(repository, "refresh_run_projection_cache", fail_rebuild)

    projections = run_projection_bundle_for_run(repository, run["id"])

    assert projections["run_snapshot"]["run_id"] == run["id"]
    assert projections["coverage"]["source_sequence"] == 1
    assert projections["task_verdict"]["source_sequence"] == 1


def test_loop_events_replay_loop_definition_projection(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nReplay loop definition.\n", encoding="utf-8")
    repository.create_loop(
        {
            "id": "loop_replay_projection",
            "name": "Loop Replay Projection",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {
                "goal": "Replay loop definition.",
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

    projections = replay_loop_projection_bundle(repository.list_domain_events(loop_stream_id("loop_replay_projection")))
    cached = repository.get_projection_record("loop_definition", "loop_replay_projection")
    cached_timeline = repository.get_projection_record("audit_timeline", "loop_replay_projection")

    assert projections["loop_definition"] == {
        "schema_version": 1,
        "kind": "event_replayed_loop_definition",
        "source_sequence": 3,
        "loop_id": "loop_replay_projection",
        "name": "Loop Replay Projection",
        "task": "Replay loop definition.",
        "completion_mode": "gatekeeper",
        "status": "active",
        "check_count": 1,
        "coverage_target_count": 2,
        "role_count": 1,
        "step_count": 1,
        "finish_step_ids": ["judge"],
    }
    assert cached["source_sequence"] == 3
    assert cached["payload"] == projections["loop_definition"]
    assert cached_timeline["source_sequence"] == 3
    assert cached_timeline["payload"] == projections["audit_timeline"]
    assert [event["event_type"] for event in projections["audit_timeline"]["events"]] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
    ]

    repository.delete_loop("loop_replay_projection")

    archived = replay_loop_projection_bundle(repository.list_domain_events(loop_stream_id("loop_replay_projection")))

    assert archived["loop_definition"]["source_sequence"] == 4
    assert archived["loop_definition"]["status"] == "archived"
    assert repository.get_projection_record("loop_definition", "loop_replay_projection")["payload"]["status"] == "archived"
    assert [event["event_type"] for event in archived["audit_timeline"]["events"]] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopArchived",
    ]


def test_run_engine_replays_current_step_projection_from_claim_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")

    engine.claim_step(
        RunEngineClaimStepRequest(
            instruction=runner_step_instruction(
                RunnerStepInstructionRequest(
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

    projections = replay_run_projections(repository, run["id"])
    cached_current_step = repository.get_projection_record("current_step", run["id"])
    cached_step_surfaces = repository.get_projection_record("step_surfaces", run["id"])

    assert projections["run_snapshot"]["lifecycle_status"] == "awaiting_actor"
    assert projections["current_step"] == {
        "schema_version": 1,
        "kind": "event_replayed_current_step",
        "source_sequence": 4,
        "run_id": run["id"],
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": actor.to_dict(),
        "claimable": True,
        "lifecycle_status": "awaiting_actor",
    }
    assert projections["step_surfaces"]["available"] is True
    assert projections["step_surfaces"]["agent_step_view"]["step_id"] == "builder"
    assert projections["step_surfaces"]["cli_summary"]["role_archetype"] == "builder"
    assert projections["step_surfaces"]["cli_step_summary"]["kind"] == "cli_step_summary"
    assert cached_current_step["payload"] == projections["current_step"]
    assert cached_step_surfaces["payload"] == projections["step_surfaces"]


def test_run_projection_replay_keeps_prior_iteration_when_event_iteration_is_malformed(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="IterationStarted",
            payload={"run_id": run["id"], "iteration": "not-a-number", "step_count": 1},
            actor=actor,
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepInstructionIssued",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": "still-not-a-number",
                "pending_actor": actor.to_dict(),
            },
            actor=actor,
        )
    )

    projections = replay_run_projections(repository, run["id"])

    assert projections["run_snapshot"]["current_iteration"] == 0
    assert projections["current_step"]["iteration"] == 0
    assert projections["current_step"]["step_id"] == "builder"


def test_run_engine_current_step_projection_replays_when_cache_missing(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    actor = ActorRef(kind="runner", id="headless")
    engine = RepositoryRunEngine(repository)
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )
    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))
    with repository.transaction() as connection:
        connection.execute(
            "DELETE FROM projection_store WHERE projection_name = ? AND projection_key = ?",
            ("current_step", run["id"]),
        )

    projection = current_step_projection_for_run(repository, run["id"])
    refreshed_cache = repository.get_projection_record("current_step", run["id"])

    assert projection["kind"] == "event_replayed_current_step"
    assert projection["source_sequence"] == 4
    assert projection["step_id"] == "builder"
    assert projection["claimable"] is True
    assert refreshed_cache["payload"] == projection


def test_run_engine_current_step_projection_replays_when_cache_is_stale(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    actor = ActorRef(kind="runner", id="headless")
    engine = RepositoryRunEngine(repository)
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )
    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))
    cached_current_step = repository.get_projection_record("current_step", run["id"])

    submitted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepSubmitted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "status": "completed",
                "summary": "Builder completed.",
            },
            actor=actor,
        )
    )
    accepted_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepAccepted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "result_status": "completed",
            },
            actor=actor,
            causation_id=submitted_event.event_id,
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepCommitted",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": 1,
                "result_status": "completed",
            },
            actor=actor,
            causation_id=accepted_event.event_id,
        )
    )
    tampered_payload = {**cached_current_step["payload"], "source_sequence": 999}
    with repository.transaction() as connection:
        connection.execute(
            """
            UPDATE projection_store
            SET payload_json = ?
            WHERE projection_name = ? AND projection_key = ?
            """,
            (json.dumps(tampered_payload), "current_step", run["id"]),
        )

    projection = current_step_projection_for_run(repository, run["id"])
    refreshed_cache = repository.get_projection_record("current_step", run["id"])

    assert cached_current_step["payload"]["source_sequence"] == 4
    assert projection["source_sequence"] == 7
    assert projection["step_id"] is None
    assert projection["claimable"] is False
    assert refreshed_cache["source_sequence"] == 7
    assert refreshed_cache["payload"] == projection


def test_run_engine_rebuilds_projection_store_from_event_replay(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)

    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=ActorRef(kind="system", id="verdict-engine"),
            verdict={"status": "continue_required", "source": "system", "summary": "Need more proof."},
        )
    )

    rebuild_run_projection_cache(repository, run["id"])
    cached = repository.get_projection_record("task_verdict", run["id"])

    assert cached["source_sequence"] == repository.latest_domain_event_sequence(run_stream_id(run["id"]))
    assert cached["payload"]["status"] == "continue_required"


def test_run_engine_replays_rich_task_verdict_projection(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="system", id="verdict-engine")

    engine.accept_evidence(
        RunEngineAcceptEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_checks",
                "step_id": "builder",
                "role_id": "builder",
                "claim": "Automated checks passed.",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )
    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection={
                "status": "weak",
                "target_count": 2,
                "covered_target_count": 1,
                "weak_target_count": 1,
                "top_gaps": [{"target_id": "done_when.manual_export", "status": "weak"}],
            },
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Accepted with a named follow-up.",
                "buckets": {
                    "proven": [{"label": "Automated checks passed.", "evidence_refs": ["ev_checks"]}],
                    "residual_risk": [{"label": "Manual export remains.", "managed": True}],
                },
            },
        )
    )

    projection = replay_run_projections(repository, run["id"])["task_verdict"]
    cached = repository.get_projection_record("task_verdict", run["id"])

    assert projection["status"] == "passed_with_residual_risk"
    assert projection["buckets"]["proven"] == [{"label": "Automated checks passed.", "evidence_refs": ["ev_checks"]}]
    assert projection["buckets"]["residual_risk"] == [{"label": "Manual export remains.", "managed": True}]
    assert "next_gap" not in projection
    assert cached["payload"] == projection


def test_event_replayed_audit_timeline_includes_iteration_lifecycle(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="runner", id="headless")

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

    timeline = replay_run_projections(repository, run["id"])["audit_timeline"]

    assert [event["event_type"] for event in timeline["events"][-2:]] == ["IterationStarted", "IterationCompleted"]
    assert timeline["events"][-1]["summary"] == "checkpointed"
