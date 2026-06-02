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


RUNNER_PARITY_LOOP_NAME = "Runner Parity Loop"
RUNNER_PARITY_SPEC_MARKDOWN = "# Task\n\nProve runner parity.\n"
RUNNER_PARITY_GOAL = "Prove runner parity."
RUNNER_PARITY_CHECK_ID = "proof"
RUNNER_PARITY_COVERAGE_TARGET_ID = "done_when.proof"
RUNNER_PARITY_MODEL = "gpt-5.4"
RUNNER_PARITY_REASONING_EFFORT = "medium"
RUNNER_PARITY_BUILDER_STEP_ID = "builder"
RUNNER_PARITY_EVIDENCE_ID = "ev_runner_parity"


def _runner_parity_compiled_spec() -> dict:
    return {
        "goal": RUNNER_PARITY_GOAL,
        "checks": [{"id": RUNNER_PARITY_CHECK_ID, "title": "Proof"}],
        "coverage_targets": [{"id": RUNNER_PARITY_COVERAGE_TARGET_ID, "label": "Required proof"}],
    }


def _runner_parity_runtime_defaults() -> dict:
    return {
        "model": RUNNER_PARITY_MODEL,
        "reasoning_effort": RUNNER_PARITY_REASONING_EFFORT,
        "max_iters": 1,
        "max_role_retries": 1,
        "delta_threshold": 0.1,
        "trigger_window": 1,
        "regression_window": 1,
        "role_models": {},
    }


def _runner_parity_record_payload(workdir: Path, spec_path: Path) -> dict:
    return {
        "workdir": str(workdir),
        "spec_path": str(spec_path),
        "spec_markdown": RUNNER_PARITY_SPEC_MARKDOWN,
        "compiled_spec": _runner_parity_compiled_spec(),
        **_runner_parity_runtime_defaults(),
    }


def create_runner_parity_run(repository: LooporaRepository, tmp_path: Path, *, run_id: str, loop_id: str) -> dict:
    workdir = tmp_path / run_id / "workdir"
    workdir.mkdir(parents=True)
    spec_path = tmp_path / run_id / "spec.md"
    spec_path.write_text(RUNNER_PARITY_SPEC_MARKDOWN, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": loop_id,
            "name": RUNNER_PARITY_LOOP_NAME,
            **_runner_parity_record_payload(workdir, spec_path),
        }
    )
    run_dir = workdir / ".loopora" / "runs" / run_id
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": run_id,
            "loop_id": loop["id"],
            "status": "queued",
            "runs_dir": str(run_dir),
            **_runner_parity_record_payload(workdir, spec_path),
        }
    )


def run_submission_flow(tmp_path: Path, *, actor: ActorRef, run_id: str, loop_id: str) -> dict:
    repository = LooporaRepository(tmp_path / f"{run_id}.db")
    create_runner_parity_run(repository, tmp_path, run_id=run_id, loop_id=loop_id)
    engine = RepositoryRunEngine(repository)
    submit_result = engine.submit_step(
        RunEngineSubmitStepRequest(
            result=StepResult(
                run_id=run_id,
                step_id=RUNNER_PARITY_BUILDER_STEP_ID,
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
                "id": RUNNER_PARITY_EVIDENCE_ID,
                "step_id": RUNNER_PARITY_BUILDER_STEP_ID,
                "role_id": RUNNER_PARITY_BUILDER_STEP_ID,
                "archetype": RUNNER_PARITY_BUILDER_STEP_ID,
                "claim": "Runner parity proof exists.",
                "method": "pytest",
                "result": "passed",
                "verifies": [f"target:{RUNNER_PARITY_COVERAGE_TARGET_ID}:covered"],
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
                    "proven": [{"label": "Required proof", "evidence_refs": [RUNNER_PARITY_EVIDENCE_ID]}],
                    "residual_risk": [{"label": "Manual follow-up remains.", "managed": True}],
                },
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
