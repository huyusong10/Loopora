from __future__ import annotations

import shlex

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command, rewrite_loopora_help_commands
from loopora.run_result_recording import run_result_is_lifecycle_failure

__all__ = [
    "cli_loop_delete_next_actions",
    "cli_loop_delete_preview_payload",
    "cli_loop_list_item",
    "cli_loop_status_payload",
    "copyable_loop_rerun_retry_command",
    "exit_with_loop_identifier_recovery",
    "loop_rerun_retry_command",
    "normalize_loop_identifier",
]

_LOOP_IDENTIFIER_LABELS = {
    "loop_or_run_id": "Loop ID or run ID",
    "loop_id": "Loop ID",
    "run_id": "Run ID",
}
_LOOP_IDENTIFIER_PLACEHOLDERS = {
    "loop_or_run_id": "<loop-or-run-id>",
    "loop_id": "<loop-id>",
    "run_id": "<run-id>",
}


def normalize_loop_identifier(identifier: str | None) -> str:
    return str(identifier or "").strip()


def exit_with_loop_identifier_recovery(
    *,
    action: str,
    identifier_kind: str,
    json_output: bool = False,
) -> None:
    payload = loop_identifier_recovery_payload(action=action, identifier_kind=identifier_kind)
    if json_output:
        from loopora.cli_common import echo_json

        echo_json(payload)
    else:
        print_loop_identifier_recovery(payload)
    raise typer.Exit(1)


def loop_identifier_recovery_payload(*, action: str, identifier_kind: str) -> dict:
    return project_next_action_readiness_contract(
        {
            "loop_recovery": "missing_loop_identifier",
            "status": "blocked_by_missing_identifier",
            "action": action,
            "required_identifier": identifier_kind,
            "required_identifier_label": _LOOP_IDENTIFIER_LABELS[identifier_kind],
            "summary": "Choose a saved Loop or Run before continuing this existing-work command.",
            "next_actions": loop_identifier_next_actions(action=action, identifier_kind=identifier_kind),
        }
    )


def loop_identifier_next_actions(*, action: str, identifier_kind: str) -> list[dict[str, str]]:
    return [
        {
            "kind": "list_saved_loops",
            "label": "List saved Loops and latest runs",
            "command": copyable_loopora_command("loopora loops list"),
        },
        {
            "kind": "open_web_saved_work",
            "label": "Open Web to review saved Loops and Runs",
            "command": copyable_loopora_command('loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742'),
        },
        {
            "kind": "retry_after_choice",
            "label": "Retry after choosing an identifier",
            "command_template": loop_identifier_retry_template(action=action, identifier_kind=identifier_kind),
        },
    ]


def loop_identifier_retry_template(*, action: str, identifier_kind: str) -> str:
    command = f"loopora loops {action} {_LOOP_IDENTIFIER_PLACEHOLDERS[identifier_kind]}"
    if action == "delete":
        command = f"{command} --dry-run"
    return rewrite_loopora_help_commands(command)


def print_loop_identifier_recovery(payload: dict) -> None:
    typer.echo("Loopora saved work needs an id")
    typer.echo(f"action: {payload['action']}")
    typer.echo(f"required identifier: {payload['required_identifier_label']}")
    typer.echo(f"summary: {payload['summary']}")
    typer.echo("next actions:")
    for action in payload["next_actions"]:
        detail = action.get("command") or action.get("command_template") or ""
        suffix = f": {detail}" if detail else ""
        typer.echo(f"- {action['label']}{suffix}")


def cli_loop_delete_next_actions(loop_id: str, *, delete_allowed: bool) -> list[dict[str, str]]:
    if not delete_allowed:
        return []
    return [
        {
            "kind": "delete_loop",
            "command": copyable_loopora_command(f"loopora loops delete {shlex.quote(loop_id)}"),
            "note": "Run this only after reviewing the dry-run scope.",
        }
    ]


def cli_loop_delete_preview_payload(preview: dict, loop_id: str) -> dict:
    payload = dict(preview)
    payload["next_actions"] = cli_loop_delete_next_actions(
        loop_id,
        delete_allowed=payload.get("delete_allowed") is True,
    )
    return project_next_action_readiness_contract(payload)


def loop_rerun_retry_command(loop_id: str, *, background: bool, json_output: bool = False) -> str:
    command = f"loopora loops rerun {shlex.quote(loop_id)}"
    if background:
        command = f"{command} --background"
    if json_output:
        command = f"{command} --json"
    return command


def copyable_loop_rerun_retry_command(loop_id: str, *, background: bool, json_output: bool = False) -> str:
    return copyable_loopora_command(loop_rerun_retry_command(loop_id, background=background, json_output=json_output))


def cli_loop_list_item(loop: dict) -> dict:
    item = dict(loop)
    item["latest_status_label"] = str(item.get("latest_status") or "draft")
    if loop_latest_run_is_lifecycle_failure(item):
        item["latest_status_label"] = "run_start_failed"
        item["latest_run_recovery"] = "retry_run_start"
        item["next_actions"] = retry_cli_run_start_actions(item.get("id"))
        project_next_action_readiness_contract(item)
    return item


def loop_latest_run_is_lifecycle_failure(loop: dict) -> bool:
    return str(loop.get("latest_status") or "").strip().lower() == "failed" and run_result_is_lifecycle_failure(
        {"error_message": loop.get("latest_error_message")}
    )


def cli_loop_status_payload(kind: str, payload: dict) -> dict:
    if kind == "loop":
        return cli_loop_status_item(payload)
    if kind == "run":
        return cli_run_status_item(payload)
    return payload


def cli_loop_status_item(loop: dict) -> dict:
    item = dict(loop)
    latest_run = latest_loop_status_run(item)
    if latest_run:
        item.setdefault("latest_run_id", latest_run.get("id"))
        item.setdefault("latest_status", latest_run.get("status") or latest_run.get("run_status"))
        item.setdefault("latest_error_message", latest_run.get("error_message"))
        if "latest_task_verdict_json" not in item and isinstance(latest_run.get("task_verdict"), dict):
            item["latest_task_verdict_json"] = latest_run["task_verdict"]
    return cli_loop_list_item(item)


def latest_loop_status_run(loop: dict) -> dict:
    runs = loop.get("runs") if isinstance(loop.get("runs"), list) else []
    latest_run_id = str(loop.get("latest_run_id") or "").strip()
    if latest_run_id:
        for run in runs:
            if isinstance(run, dict) and str(run.get("id") or "").strip() == latest_run_id:
                return run
    for run in runs:
        if isinstance(run, dict):
            return run
    return {}


def cli_run_status_item(run: dict) -> dict:
    item = dict(run)
    item["status_label"] = str(item.get("status") or item.get("run_status") or "unknown")
    if str(item.get("status") or item.get("run_status") or "").strip().lower() == "failed" and run_result_is_lifecycle_failure(item):
        item["status_label"] = "run_start_failed"
        item["run_recovery"] = "retry_run_start"
        actions = retry_cli_run_start_actions(item.get("loop_id"))
        if actions:
            item["next_actions"] = actions
            project_next_action_readiness_contract(item)
    return item


def retry_cli_run_start_actions(loop_id: object) -> list[dict[str, str]]:
    normalized_loop_id = str(loop_id or "").strip()
    if not normalized_loop_id:
        return []
    return [
        {
            "kind": "retry_cli_run_start",
            "command": copyable_loop_rerun_retry_command(normalized_loop_id, background=False),
        }
    ]
