from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineIssueVerdictRequest,
    RunEngineRecordStepEvidenceRequest,
    RunEngineSubmitStepRequest,
)
from loopora.events import run_stream_id
from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import ActorRef, StepResult, StepResultStatus
from loopora.runners import agent_runner_actor, headless_runner_actor


def _create_run(repository: LooporaRepository, tmp_path: Path, *, run_id: str, loop_id: str) -> dict:
    workdir = tmp_path / run_id / "workdir"
    workdir.mkdir(parents=True)
    spec_path = tmp_path / run_id / "spec.md"
    spec_markdown = "# Task\n\nProve runner parity.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": loop_id,
            "name": "Runner Parity Loop",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {
                "goal": "Prove runner parity.",
                "checks": [{"id": "proof", "title": "Proof"}],
                "coverage_targets": [{"id": "done_when.proof", "label": "Required proof"}],
            },
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
    run_dir = workdir / ".loopora" / "runs" / run_id
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": run_id,
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {
                "goal": "Prove runner parity.",
                "checks": [{"id": "proof", "title": "Proof"}],
                "coverage_targets": [{"id": "done_when.proof", "label": "Required proof"}],
            },
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


def _run_submission_flow(tmp_path: Path, *, actor: ActorRef, run_id: str, loop_id: str) -> dict:
    repository = LooporaRepository(tmp_path / f"{run_id}.db")
    _create_run(repository, tmp_path, run_id=run_id, loop_id=loop_id)
    engine = RepositoryRunEngine(repository)
    submit_result = engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run_id,
                step_id="builder",
                iteration=1,
                actor=actor,
                status=StepResultStatus.COMPLETED,
                summary="Builder produced direct evidence.",
            )
        )
    )
    engine.record_step_evidence(
        RunEngineRecordStepEvidenceRequest(
            run_id=run_id,
            evidence_entry={
                "id": "ev_runner_parity",
                "step_id": "builder",
                "role_id": "builder",
                "archetype": "builder",
                "claim": "Runner parity proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
                "artifact_refs": [{"kind": "workspace", "uri": "proof.txt"}],
            },
            coverage_projection={
                "status": "covered",
                "target_count": 1,
                "covered_target_count": 1,
                "top_gaps": [],
            },
            actor=actor,
            correlation_id=submit_result.submitted_event.correlation_id,
            causation_id=submit_result.submitted_event.event_id,
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run_id,
            verdict={
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Same runner evidence, same verdict.",
                "buckets": {
                    "proven": [{"label": "Required proof", "evidence_refs": ["ev_runner_parity"]}],
                    "residual_risk": [{"label": "Manual follow-up remains.", "managed": True}],
                },
                "next_gap": [{"target_id": "done_when.follow_up", "status": "weak"}],
            },
            actor=actor,
        )
    )
    projections = replay_run_projections(repository, run_id)
    events = repository.list_domain_events(run_stream_id(run_id))
    return {
        "events": [_stable_event(event) for event in events if event.event_type != "RunCreated"],
        "evidence_ledger": _stable_projection(projections["evidence_ledger"]),
        "coverage": _stable_projection(projections["coverage"]),
        "task_verdict": _stable_projection(projections["task_verdict"]),
    }


def test_headless_and_agent_runner_submissions_replay_to_same_domain_outputs(tmp_path: Path) -> None:
    headless = _run_submission_flow(
        tmp_path,
        actor=headless_runner_actor(),
        run_id="run_runner_parity_headless",
        loop_id="loop_runner_parity_headless",
    )
    agent = _run_submission_flow(
        tmp_path,
        actor=agent_runner_actor("codex"),
        run_id="run_runner_parity_agent",
        loop_id="loop_runner_parity_agent",
    )

    assert agent == headless


def _stable_event(event) -> dict:
    return {
        "event_type": event.event_type,
        "payload": _stable_projection(event.payload),
    }


def _stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_projection(item)
            for key, item in value.items()
            if key not in {"event_id", "occurred_at"}
        }
    if isinstance(value, list):
        return [_stable_projection(item) for item in value]
    if isinstance(value, str) and value.startswith(("run_runner_parity_", "loop_runner_parity_")):
        return "<id>"
    return value
