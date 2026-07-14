from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_common import call_spawn_background_worker, echo_json, get_service, logger
from loopora.cli_run_output import (
    loop_create_result_payload,
    print_loop_created,
    print_run_contract_summary,
    print_run_result,
    print_task_verdict,
    run_result_payload,
)
from loopora.cli_runtime import set_worker_spawner
from loopora.cli_strategy_source_support import LoopBuildRequest, build_loop_kwargs
from loopora.diagnostics import log_event, log_exception
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR, background_worker_start_failure_summary
from loopora.service import LooporaError
from loopora.utils import utc_now

__all__ = [
    "BackgroundRunStartError",
    "LoopCreateRequest",
    "background_run_start_failure_payload",
    "background_worker_command",
    "create_and_maybe_start_loop",
    "exit_with_background_run_start_failure",
    "loop_create_result_payload",
    "print_loop_created",
    "print_run_contract_summary",
    "print_run_result",
    "print_task_verdict",
    "run_result_payload",
    "spawn_background_worker",
    "start_run",
]


class BackgroundRunStartError(LooporaError):
    def __init__(self, run: dict, *, loop: dict | None = None) -> None:
        super().__init__(BACKGROUND_WORKER_START_ERROR)
        self.run = run
        self.loop = loop


def background_worker_command(run_id: str) -> list[str]:
    return [sys.executable, "-m", "loopora", "_execute-run", run_id]


def spawn_background_worker(service, run: dict) -> dict:
    run_dir = Path(run["runs_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "background_worker.log"
    command = background_worker_command(run["id"])
    log_handle = log_path.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            cwd=run["workdir"],
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
    except OSError as exc:
        summary = background_worker_start_failure_summary()
        service.repository.update_run(
            run["id"],
            status="failed",
            finished_at=utc_now(),
            error_message=BACKGROUND_WORKER_START_ERROR,
            summary_md=summary,
        )
        service.append_run_event(
            run["id"],
            "run_aborted",
            {
                "role": None,
                "attempts": 1,
                "degraded": False,
                "error": BACKGROUND_WORKER_START_ERROR,
            },
        )
        log_exception(
            logger,
            "cli.background_worker.spawn_failed",
            "Failed to spawn background worker",
            error=exc,
            run_id=run["id"],
            workdir=run.get("workdir"),
            log_path=log_path,
            command=command,
        )
        raise LooporaError(BACKGROUND_WORKER_START_ERROR) from exc
    finally:
        log_handle.close()

    service.repository.update_run(run["id"], runner_pid=process.pid)
    service.append_run_event(
        run["id"],
        "background_worker_spawned",
        {
            "pid": process.pid,
            "command": command,
            "log_path": str(log_path),
        },
    )
    log_event(
        logger,
        logging.INFO,
        "cli.background_worker.spawned",
        "Spawned background worker for run",
        run_id=run["id"],
        workdir=run.get("workdir"),
        worker_pid=process.pid,
        log_path=log_path,
        command=command,
    )
    return service.get_run(run["id"])


set_worker_spawner(spawn_background_worker)


def start_run(service, loop_id: str, *, background: bool, continue_saved_loop: bool = False) -> dict:
    if background:
        run = service.start_next_run(loop_id) if continue_saved_loop else service.start_run(loop_id)
        try:
            return call_spawn_background_worker(service, run)
        except LooporaError as exc:
            if str(exc) != BACKGROUND_WORKER_START_ERROR:
                raise
            raise BackgroundRunStartError(_failed_background_run(service, run)) from exc
    return service.rerun(loop_id, background=False)


def _failed_background_run(service, run: dict) -> dict:
    get_run = getattr(service, "get_run", None)
    if callable(get_run):
        try:
            refreshed = get_run(run["id"])
        except (AttributeError, KeyError, LooporaError, TypeError):
            refreshed = None
        if isinstance(refreshed, dict) and refreshed:
            return refreshed
    return {
        **run,
        "status": "failed",
        "error_message": BACKGROUND_WORKER_START_ERROR,
    }


def background_run_start_failure_payload(
    failure: BackgroundRunStartError,
    *,
    retry_command: str = "",
) -> dict[str, object]:
    copyable_retry_command = copyable_loopora_command(retry_command) if retry_command else ""
    next_actions: list[dict[str, str]] = []
    if copyable_retry_command:
        next_actions = [{"kind": "retry_cli_run_start", "command": copyable_retry_command}]
    run_id = str(failure.run.get("id") or "").strip()
    loop_id = str(failure.run.get("loop_id") or (failure.loop or {}).get("id") or "").strip()
    payload: dict[str, object] = {
        "cli_run_start_recovery_summary": {
            "ready": False,
            "run_recovery": "retry_run_start",
            "run_start_error": BACKGROUND_WORKER_START_ERROR,
            "run_id": run_id,
            "loop_id": loop_id,
            "next_action_kinds": _cli_action_kinds(next_actions),
        },
        "status": "error",
        "error": BACKGROUND_WORKER_START_ERROR,
        "run_start_error": BACKGROUND_WORKER_START_ERROR,
        "run_recovery": "retry_run_start",
        "run": run_result_payload(failure.run, json_output=True, retry_command=copyable_retry_command),
    }
    if failure.loop:
        payload["loop"] = failure.loop
    if next_actions:
        payload["next_actions"] = next_actions
    project_next_action_readiness_contract(payload, summary_key="cli_run_start_recovery_summary")
    return payload


def _cli_action_kinds(actions: list[dict[str, str]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def exit_with_background_run_start_failure(
    failure: BackgroundRunStartError,
    *,
    json_output: bool,
    retry_command: str = "",
) -> None:
    if json_output:
        echo_json(background_run_start_failure_payload(failure, retry_command=retry_command))
        raise typer.Exit(code=1)
    if failure.loop:
        print_loop_created(failure.loop)
    print_run_result(failure.run)
    typer.secho(f"run_start_error: {BACKGROUND_WORKER_START_ERROR}", fg=typer.colors.RED, err=True)
    if retry_command:
        typer.secho(f"retry: {copyable_loopora_command(retry_command)}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@dataclass(frozen=True)
class LoopCreateRequest(LoopBuildRequest):
    start: bool
    background: bool


def create_and_maybe_start_loop(request: LoopCreateRequest) -> tuple[dict, dict | None]:
    if request.background and not request.start:
        raise LooporaError("--background requires --start")
    log_event(
        logger,
        logging.INFO,
        "cli.loop.create.requested",
        "CLI requested loop creation",
        workdir=request.workdir,
        spec_path=request.spec,
        orchestration_id=request.orchestration_id,
        start=request.start,
        background=request.background,
        completion_mode=request.completion_mode,
    )
    service = get_service()
    loop = service.create_loop(**build_loop_kwargs(request))
    try:
        run = start_run(service, loop["id"], background=request.background) if request.start else None
    except BackgroundRunStartError as exc:
        raise BackgroundRunStartError(exc.run, loop=loop) from exc
    log_event(
        logger,
        logging.INFO,
        "cli.loop.create.completed",
        "CLI created loop successfully",
        loop_id=loop["id"],
        workdir=loop.get("workdir"),
        run_id=run.get("id") if run else None,
        start=request.start,
        background=request.background,
    )
    return loop, run
