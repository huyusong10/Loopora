from __future__ import annotations

import shlex

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_run_contract_output import print_run_contract_anchor as print_run_contract_anchor
from loopora.cli_run_contract_output import print_run_contract_summary as print_run_contract_summary
from loopora.cli_task_verdict_output import print_task_verdict as print_task_verdict
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run


def print_loop_created(loop: dict) -> None:
    typer.echo(f"loop: {loop['id']}")
    if loop.get("name"):
        typer.echo(f"name: {loop['name']}")
    if loop.get("workdir"):
        typer.echo(f"workdir: {loop['workdir']}")


def loop_create_result_payload(loop: dict, result: dict | None) -> dict[str, object]:
    return {
        "status": "started" if result is not None else "created",
        "loop": loop,
        "run": run_result_payload(result, json_output=True) if result is not None else None,
    }


def run_result_payload(
    result: dict,
    *,
    json_output: bool = False,
    retry_command: str = "",
) -> dict[str, object]:
    payload: dict[str, object] = dict(result)
    recovery = _run_recovery_projection(result, json_output=json_output, retry_command=retry_command)
    if not recovery:
        return payload
    payload["status_label"] = recovery["status_label"]
    payload["run_recovery"] = recovery["run_recovery"]
    next_action = recovery.get("next_action")
    if isinstance(next_action, dict):
        existing_actions = payload.get("next_actions")
        if isinstance(existing_actions, list):
            payload["next_actions"] = [*existing_actions, next_action]
        else:
            payload["next_actions"] = [next_action]
        project_next_action_readiness_contract(payload)
    return payload


def print_run_result(result: dict) -> None:
    from loopora.cli_common import echo_json

    typer.echo(f"run: {result['id']}")
    typer.echo(f"run_status: {run_status_from_run(result)}")
    _print_run_recovery(result)
    typer.echo(f"run_dir: {result['runs_dir']}")
    print_run_contract_summary(result)
    print_task_verdict(task_verdict_from_run(result))
    if result.get("last_verdict_json"):
        typer.echo("raw_last_verdict_json:")
        echo_json(result["last_verdict_json"])


def _print_run_recovery(result: dict) -> None:
    recovery = _run_recovery_projection(result)
    if not recovery:
        return
    typer.echo(f"run_status_label: {recovery['status_label']}")
    typer.echo(f"run_recovery: {recovery['run_recovery']}")
    next_action = recovery.get("next_action")
    if isinstance(next_action, dict):
        command = str(next_action.get("command") or "").strip()
        if command:
            typer.echo(f"run_recovery_command: {command}")


def _run_recovery_projection(
    result: dict,
    *,
    json_output: bool = False,
    retry_command: str = "",
) -> dict[str, object]:
    if run_status_from_run(result) != "failed" or not run_result_is_lifecycle_failure(result):
        return {}
    command = retry_command.strip() or _default_run_recovery_command(result, json_output=json_output)
    recovery: dict[str, object] = {
        "status_label": "run_start_failed",
        "run_recovery": "retry_run_start",
    }
    if command:
        recovery["next_action"] = {"kind": "retry_run_start", "command": command}
    return recovery


def _default_run_recovery_command(result: dict, *, json_output: bool = False) -> str:
    loop_id = str(result.get("loop_id") or "").strip()
    if not loop_id:
        return ""
    command = f"loopora loops rerun {shlex.quote(loop_id)}"
    if json_output:
        command = f"{command} --json"
    return copyable_loopora_command(command)
