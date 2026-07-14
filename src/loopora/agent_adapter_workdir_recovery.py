from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.workdir_inputs import workdir_path_state


@dataclass(frozen=True)
class AdapterWorkdirRetryPolicy:
    command: str = ""
    entry_source: str = ""
    before_readiness: bool = False


def adapter_workdir_state(workdir: Path | str | None) -> dict[str, object]:
    state = workdir_path_state(workdir)
    root = str(state["workdir"])
    if state["status"] == "required":
        return {
            "status": "required",
            "workdir": root,
            "usable_for_agent_entries": False,
            "usable_for_agent_runtime": False,
            "summary": "Target project directory is required; choose a project directory before managing Agent entries.",
            "error": "workdir is required",
            "commands": {},
        }
    if state["status"] == "unavailable":
        return {
            "status": "unavailable",
            "workdir": root,
            "usable_for_agent_entries": False,
            "usable_for_agent_runtime": False,
            "summary": "Target project directory cannot be inspected; choose a readable project directory before managing Agent entries.",
            "error": "workdir could not be inspected",
            "commands": {},
        }
    if state["status"] == "missing":
        create_command = f"mkdir -p {shlex.quote(root)}"
        return {
            "status": "missing",
            "workdir": root,
            "usable_for_agent_entries": False,
            "usable_for_agent_runtime": False,
            "summary": "Target project directory does not exist yet; create it before managing Agent entries.",
            "commands": {"create": create_command},
        }
    if state["status"] == "not_directory":
        return {
            "status": "not_directory",
            "workdir": root,
            "usable_for_agent_entries": False,
            "usable_for_agent_runtime": False,
            "summary": "Target project path exists but is not a directory; choose a project directory for Agent entries.",
            "commands": {},
        }
    return {
        "status": "ready",
        "workdir": root,
        "usable_for_agent_entries": True,
        "usable_for_agent_runtime": True,
        "summary": "",
        "commands": {},
    }


def adapter_workdir_recovery_payload(
    adapter: str,
    *,
    action: str,
    workdir_state: dict[str, object],
    retry_policy: AdapterWorkdirRetryPolicy | None = None,
) -> dict[str, object]:
    root = str(workdir_state.get("workdir") or "")
    label = adapter_label(adapter)
    policy = retry_policy or AdapterWorkdirRetryPolicy()
    command_action = policy.command or _default_retry_command(adapter=adapter, action=action, root=root)
    doctor_command = copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(root)}")
    prefixed_retry_command = copyable_loopora_command(command_action, entry_source=policy.entry_source)
    commands = workdir_state.get("commands") if isinstance(workdir_state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "")
    actions: list[dict[str, str]] = []
    workdir_action = (
        {"kind": "create_workdir", "command": create_command}
        if create_command
        else {"kind": "choose_workdir"}
    )
    actions.append(workdir_action)
    workdir_action_kind = str(workdir_action.get("kind") or "")
    confirm_action = {"kind": "confirm_readiness"}
    retry_action = {"kind": f"retry_{action}"}
    if create_command:
        confirm_action["command"] = doctor_command
        retry_action["command"] = prefixed_retry_command
    if policy.before_readiness:
        retry_action["after_action"] = workdir_action_kind
        confirm_action["after_action"] = str(retry_action.get("kind") or "")
        actions.append(retry_action)
        actions.append(confirm_action)
    else:
        confirm_action["after_action"] = workdir_action_kind
        retry_action["after_action"] = str(confirm_action.get("kind") or "")
        actions.append(confirm_action)
        actions.append(retry_action)
    summary = str(workdir_state.get("summary") or "")
    summary_payload = {
        "ready": False,
        "loop_recovery": "adapter_workdir_unavailable",
        "status": "blocked_by_workdir",
        "adapter": adapter,
        "action": action,
        "workdir": root,
        "workdir_state_status": str(workdir_state.get("status") or ""),
        "next_action_kinds": _adapter_workdir_action_kinds(actions),
    }
    payload = {
        "adapter_workdir_recovery_summary": summary_payload,
        "loop_recovery": "adapter_workdir_unavailable",
        "status": "blocked_by_workdir",
        "adapter": adapter,
        "label": label,
        "action": action,
        "workdir": root,
        "workdir_state": workdir_state,
        "summary": summary,
        "error": summary,
        "next_actions": actions,
    }
    _project_adapter_workdir_action_contract(payload)
    return payload


def _project_adapter_workdir_action_contract(payload: dict[str, object]) -> None:
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    action_kinds = _adapter_workdir_action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get("adapter_workdir_recovery_summary")
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _adapter_workdir_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _default_retry_command(*, adapter: str, action: str, root: str) -> str:
    quoted_adapter = shlex.quote(str(adapter))
    quoted_root = shlex.quote(root)
    return {
        "install": f"loopora init {quoted_adapter} --workdir {quoted_root}",
        "check": f"loopora init {quoted_adapter} --workdir {quoted_root} --check",
        "uninstall": f"loopora uninstall {quoted_adapter} --workdir {quoted_root}",
        "plan": f"loopora agent {quoted_adapter} plan --workdir {quoted_root}",
        "run": f"loopora agent {quoted_adapter} run --workdir {quoted_root}",
        "next": f"loopora agent {quoted_adapter} next --workdir {quoted_root}",
        "submit": f"loopora agent {quoted_adapter} submit --result-file <result-file> --workdir {quoted_root}",
    }[action]
