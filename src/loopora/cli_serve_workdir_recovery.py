from __future__ import annotations

from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.cli_serve_command_projection import serve_retry_command
from loopora.cli_serve_recovery_projection import project_serve_next_action_contract, serve_action_kinds
from loopora.web_request_context import _is_loopback_host
from loopora.workdir_inputs import normalize_recoverable_workdir


def serve_startup_workdir(workdir: Path | None) -> str:
    if workdir is None:
        return ""
    return str(normalize_recoverable_workdir(workdir, action="serve"))


def serve_workdir_recovery_payload(
    *,
    workdir: Path | None,
    host: str,
    port: int,
    allow_unsafe_open: bool,
    auth_token_configured: bool,
) -> dict[str, object]:
    state = dict(adapter_workdir_state(workdir))
    state["summary"] = _serve_workdir_summary(str(state.get("status") or ""))
    next_actions = _serve_workdir_next_actions(
        state,
        host=host,
        port=port,
        allow_unsafe_open=allow_unsafe_open,
    )
    network_auth_note = _serve_workdir_network_auth_note(
        host=host,
        auth_token_configured=auth_token_configured,
    )
    payload = {
        "serve_workdir_recovery_summary": {
            "ready": False,
            "status": "blocked_by_workdir",
            "surface": "cli_serve",
            "action": "serve",
            "workdir": state["workdir"],
            "workdir_state_status": str(state.get("status") or ""),
            "next_action_kinds": serve_action_kinds(next_actions),
            "network_auth_required": bool(network_auth_note),
        },
        "status": "blocked_by_workdir",
        "surface": "cli_serve",
        "action": "serve",
        "workdir": state["workdir"],
        "workdir_state": state,
        "summary": state["summary"],
        "next_actions": next_actions,
        "network_auth_note": network_auth_note,
    }
    project_serve_next_action_contract(payload, summary_key="serve_workdir_recovery_summary")
    return payload


def _serve_workdir_summary(status: str) -> str:
    if status == "missing":
        return "Target project directory does not exist yet; create it before opening Web."
    if status == "not_directory":
        return "Target project path exists but is not a directory; choose a project directory before opening Web."
    if status == "unavailable":
        return "Target project directory cannot be inspected; choose a readable project directory before opening Web."
    return "Target project directory is required; choose a project directory before opening Web."


def _serve_workdir_next_actions(
    state: dict[str, object],
    *,
    host: str,
    port: int,
    allow_unsafe_open: bool,
) -> list[dict[str, str]]:
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "")
    workdir = str(state.get("workdir") or "")
    actions: list[dict[str, str]] = []
    if create_command:
        actions.append({"kind": "create_workdir", "command": create_command})
    else:
        actions.append({"kind": "choose_workdir"})
    confirm_action = {"kind": "confirm_readiness"}
    retry_action = {"kind": "retry_web_start"}
    if workdir and create_command:
        confirm_action["command"] = copyable_loopora_command(
            f"loopora doctor --workdir {shlex.quote(workdir)} --web-host {shlex.quote(str(host))} --web-port {port}"
        )
        retry_action["command"] = copyable_loopora_command(
            serve_retry_command(
                workdir=workdir,
                host=host,
                port=port,
                allow_unsafe_open=allow_unsafe_open,
            )
        )
    actions.append(confirm_action)
    actions.append(retry_action)
    for action in actions[1:]:
        action["after_action"] = str(actions[0].get("kind") or "")
    return actions


def _serve_workdir_network_auth_note(*, host: str, auth_token_configured: bool) -> str:
    if _is_loopback_host(host):
        return ""
    if auth_token_configured:
        return "Keep the auth token configured when retrying Web start; token values are not printed."
    return "Configure --auth-token or LOOPORA_AUTH_TOKEN before retrying Web start on a non-loopback host."
