from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import RepositoryRunEngine, RunEngineAdvanceStatus, RunEngineFailRunRequest, RunEngineStopRunRequest
from loopora.events import run_stream_id
from loopora.kernel import ActorRef


def test_run_engine_records_non_success_terminal_events_directly(tmp_path: Path) -> None:
    stop_repository = LooporaRepository(tmp_path / "stop.db")
    fail_repository = LooporaRepository(tmp_path / "fail.db")
    stopped_run = _create_run(stop_repository, tmp_path / "stop", run_id="run_stopped", loop_id="loop_stopped")
    failed_run = _create_run(fail_repository, tmp_path / "fail", run_id="run_failed", loop_id="loop_failed")
    actor = ActorRef(kind="system", id="run-engine")

    stopped = RepositoryRunEngine(stop_repository).stop(
        RunEngineStopRunRequest(run_id=stopped_run["id"], actor=actor, reason="user_requested_stop")
    )
    failed = RepositoryRunEngine(fail_repository).fail(
        RunEngineFailRunRequest(run_id=failed_run["id"], actor=actor, reason="executor_crashed")
    )

    stopped_events = stop_repository.list_domain_events(run_stream_id(stopped_run["id"]))
    failed_events = fail_repository.list_domain_events(run_stream_id(failed_run["id"]))

    assert stopped.status == RunEngineAdvanceStatus.STOPPED
    assert failed.status == RunEngineAdvanceStatus.FAILED
    assert stopped_events[-1].event_type == "RunStopped"
    assert stopped_events[-1].payload["reason"] == "user_requested_stop"
    assert failed_events[-1].event_type == "RunFailed"
    assert failed_events[-1].payload["reason"] == "executor_crashed"
    assert stop_repository.get_run(stopped_run["id"])["status"] == "queued"
    assert fail_repository.get_run(failed_run["id"])["status"] == "queued"


def _create_run(repository: LooporaRepository, tmp_path: Path, *, run_id: str, loop_id: str) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    spec_path = tmp_path / "spec.md"
    spec_markdown = "# Task\n\nProve it.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": loop_id,
            "name": "Lifecycle Command Loop",
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
    run_dir = workdir / ".loopora" / "runs" / run_id
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": run_id,
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
