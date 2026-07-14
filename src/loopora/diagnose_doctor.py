from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from loopora.agent_adapters import (
    adapter_first_task_handoff_policy,
    adapter_first_task_message_example,
    adapter_first_task_message_example_state,
    check_agent_adapter,
)
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_native_adapter_contracts import AGENT_ADAPTER_KINDS
from loopora.diagnose_doctor_identity import (
    package_identity_report as package_identity_report,
    package_source_label as package_source_label,
)
from loopora.diagnose_doctor_actions import (
    doctor_readiness_command as _doctor_readiness_command,
    doctor_next_action_items as _doctor_next_action_items,
    target_required_doctor_next_action_items as _target_required_next_action_items,
)
from loopora.diagnose_doctor_projection import (
    doctor_actions_with_command_readiness as _doctor_actions_with_command_readiness,
    doctor_action_step as doctor_action_step,
    doctor_json_payload as doctor_json_payload,
    doctor_summary as doctor_summary,
    first_task_handoff_blockers as _first_task_handoff_blockers,
    first_task_handoff_executable as _first_task_handoff_executable,
    next_steps_from_actions as _next_steps_from_actions,
)
from loopora.diagnose_doctor_public import (
    DOCTOR_PUBLIC_SCHEMA_VERSION as DOCTOR_PUBLIC_SCHEMA_VERSION,
    PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND as PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND,
    doctor_public_json_payload as doctor_public_json_payload,
    doctor_public_summary as doctor_public_summary,
    doctor_web_readiness_blockers as _web_readiness_blockers,
)
from loopora.diagnose_doctor_web_state import (
    DEFAULT_WEB_HOST as DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT as DEFAULT_WEB_PORT,
    commandless_doctor_web_report as _commandless_web_report,
    doctor_app_state_report as _app_state_report,
    doctor_app_state_with_web_recovery as _app_state_with_web_recovery,
    doctor_target_required_app_state as _target_required_app_state,
    doctor_web_report as _doctor_web_report,
)
from loopora.diagnose_doctor_workdir_state import (
    agent_entry_blocked_by_workdir as _agent_entry_blocked_by_workdir,
    doctor_workdir_state as _workdir_state,
    target_required_doctor_workdir_state as _target_required_workdir_state,
)
from loopora.web_bind_preflight import next_available_web_port as next_available_web_port, probe_web_bind as probe_web_bind

DOCTOR_SCHEMA_VERSION = 2


def build_doctor_report(
    *,
    workdir: Path | str,
    web_host: str = DEFAULT_WEB_HOST,
    web_port: int = DEFAULT_WEB_PORT,
    web_already_running: bool = False,
    web_auth_enabled: bool | None = None,
) -> dict[str, Any]:
    raw_root = Path(workdir).expanduser()
    workdir_state = _workdir_state(raw_root)
    root = Path(str(workdir_state.get("workdir") or raw_root))
    agent_entries = [
        _agent_entry_report(adapter, root)
        if workdir_state["usable_for_agent_entries"]
        else _agent_entry_blocked_by_workdir(adapter, workdir_state=workdir_state)
        for adapter in AGENT_ADAPTER_KINDS
    ]
    ready_entries = [entry for entry in agent_entries if entry["ready"]]
    attention_entries = [entry for entry in agent_entries if _entry_needs_attention(entry)]
    workdir_usable = workdir_state["usable_for_agent_entries"] is True
    web = _web_report(
        web_host,
        web_port,
        startup_workdir=root if workdir_usable else None,
        web_already_running=web_already_running,
        web_auth_enabled=web_auth_enabled,
    )
    app_state = _app_state_report(root, include_commands=workdir_usable)
    if workdir_usable:
        app_state = _app_state_with_web_recovery(app_state, web)
    web = {**web, "readiness_blockers": _web_readiness_blockers(app_state, web)}
    status = _overall_status(
        ready_entries=ready_entries,
        attention_entries=attention_entries,
        app_state=app_state,
        web=web,
    )
    agent_entry_ready = bool(ready_entries)
    strict_ready = status == "ready"
    first_task_handoff_executable = _first_task_handoff_executable(
        workdir_state=workdir_state,
        agent_entry_ready=agent_entry_ready,
        app_state=app_state,
    )
    first_task_handoff_blockers = _first_task_handoff_blockers(
        workdir_state=workdir_state,
        agent_entry_ready=agent_entry_ready,
        app_state=app_state,
    )
    next_action_items = _doctor_next_action_items(
        root,
        workdir_state=workdir_state,
        agent_entries=agent_entries,
        app_state=app_state,
        web=web,
    )
    next_action_items = _doctor_actions_with_command_readiness(
        next_action_items,
        first_task_handoff_blockers=first_task_handoff_blockers,
    )
    primary_next_action_kind = _primary_next_action_kind(next_action_items)
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "status": status,
        "ready": agent_entry_ready,
        "agent_entry_ready": agent_entry_ready,
        "strict_ready": strict_ready,
        "workdir": str(root),
        "workdir_state": workdir_state,
        "package": _package_report(),
        "app_state": app_state,
        "web": web,
        "commands": {"confirm_readiness": _doctor_readiness_command(root, web=web)},
        "agent_entries": agent_entries,
        "ready_adapter_count": len(ready_entries),
        "attention_adapter_count": len(attention_entries),
        "recommended_adapter": ready_entries[0]["adapter"] if ready_entries else "",
        "first_task_message_example": adapter_first_task_message_example(),
        "first_task_message_example_state": adapter_first_task_message_example_state(),
        "first_task_handoff_policy": _copyable_first_task_handoff_policy(root),
        "first_task_handoff_executable": first_task_handoff_executable,
        "first_task_handoff_blockers": first_task_handoff_blockers,
        "primary_next_action_kind": primary_next_action_kind,
        "next_action_items": next_action_items,
        "next_steps": _next_steps_from_actions(next_action_items),
    }


def build_target_required_doctor_report(
    *,
    web_host: str = DEFAULT_WEB_HOST,
    web_port: int = DEFAULT_WEB_PORT,
    web_already_running: bool = False,
    web_auth_enabled: bool | None = None,
) -> dict[str, Any]:
    workdir_state = _target_required_workdir_state()
    agent_entries = [_agent_entry_blocked_by_workdir(adapter, workdir_state=workdir_state) for adapter in AGENT_ADAPTER_KINDS]
    app_state = _target_required_app_state()
    web = _commandless_web_report(
        _web_report(
            web_host,
            web_port,
            startup_workdir=None,
            web_already_running=web_already_running,
            web_auth_enabled=web_auth_enabled,
        )
    )
    first_task_handoff_blockers = _first_task_handoff_blockers(
        workdir_state=workdir_state,
        agent_entry_ready=False,
        app_state=app_state,
    )
    next_action_items = _target_required_next_action_items()
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "status": "target_required",
        "ready": False,
        "agent_entry_ready": False,
        "strict_ready": False,
        "target_project_required": True,
        "workdir": "",
        "workdir_state": workdir_state,
        "package": _package_report(),
        "app_state": app_state,
        "web": web,
        "commands": {},
        "agent_entries": agent_entries,
        "ready_adapter_count": 0,
        "attention_adapter_count": 0,
        "recommended_adapter": "",
        "first_task_message_example": "",
        "first_task_message_example_state": adapter_first_task_message_example_state(),
        "first_task_handoff_policy": {
            "preferred_source": "completed_fit_review",
            "fallback_source": "unavailable_until_target_project",
        },
        "first_task_handoff_executable": False,
        "first_task_handoff_blockers": first_task_handoff_blockers,
        "primary_next_action_kind": _primary_next_action_kind(next_action_items),
        "next_action_items": next_action_items,
        "next_steps": _next_steps_from_actions(next_action_items),
    }


def _copyable_first_task_handoff_policy(root: Path) -> dict[str, str]:
    policy = adapter_first_task_handoff_policy(workdir=root)
    raw_fit_command = str(policy.get("fit_command") or "loopora fit")
    fit_command = copyable_loopora_command(raw_fit_command)
    policy["fit_command"] = fit_command
    policy["copy_rule"] = str(policy.get("copy_rule") or "").replace(raw_fit_command, fit_command)
    return policy


def _primary_next_action_kind(actions: list[dict[str, Any]]) -> str:
    for action in actions:
        kind = str(action.get("kind") or "").strip()
        if kind:
            return kind
    return ""


def _agent_entry_report(adapter: str, root: Path) -> dict[str, Any]:
    result = check_agent_adapter(adapter, workdir=root)
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    check_status = str(result.get("check_status") or "fail")
    install_state = str(recovery.get("state") or result.get("status") or "unknown")
    details_are_expected = recovery.get("details_are_expected") is True
    checks = [item for item in list(result.get("checks") or []) if isinstance(item, dict)]
    failed_checks = [
        {
            "name": str(item.get("name") or ""),
            "path": str(item.get("path") or ""),
            "message": str(item.get("message") or ""),
        }
        for item in checks
        if item.get("status") != "pass"
    ]
    entry = {
        "adapter": adapter,
        "label": str(result.get("label") or adapter),
        "ready": check_status == "pass",
        "check_status": check_status,
        "install_state": install_state,
        "summary": str(recovery.get("summary") or ""),
        "details_are_expected": details_are_expected,
        "commands": _agent_entry_commands(adapter, root, recovery=recovery),
        "next_action": _agent_entry_next_action(check_status=check_status, install_state=install_state),
    }
    if failed_checks and not details_are_expected:
        entry["failed_checks"] = failed_checks
    return entry


def _agent_entry_commands(adapter: str, root: Path, *, recovery: dict[str, Any]) -> dict[str, str]:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}")
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = copyable_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))} --check")
    agent_check_command = copyable_loopora_command(f"loopora agent {adapter} check --workdir {shlex.quote(str(root))}")
    return {
        "install": install_command,
        "install_check": check_command,
        "agent_check": agent_check_command,
    }


def _agent_entry_next_action(*, check_status: str, install_state: str) -> str:
    if check_status == "pass":
        return "return_to_agent"
    if install_state == "not_installed":
        return "install_agent_entry"
    return "inspect_or_repair_agent_entry"


def _entry_needs_attention(entry: dict[str, Any]) -> bool:
    if entry.get("ready") is True:
        return False
    return str(entry.get("install_state") or "") not in {"not_installed", "blocked_by_workdir"}


def _overall_status(
    *,
    ready_entries: list[dict[str, Any]],
    attention_entries: list[dict[str, Any]],
    app_state: dict[str, Any],
    web: dict[str, Any],
) -> str:
    web_needs_attention = web.get("start_available") is False
    if ready_entries and (attention_entries or app_state.get("needs_attention") or web_needs_attention):
        return "ready_with_warnings"
    if ready_entries:
        return "ready"
    return "not_ready"


def _package_report() -> dict[str, Any]:
    return package_identity_report()


def _web_report(
    host: str,
    port: int,
    *,
    startup_workdir: Path | None = None,
    web_already_running: bool = False,
    web_auth_enabled: bool | None = None,
) -> dict[str, Any]:
    return _doctor_web_report(
        host,
        port,
        startup_workdir=startup_workdir,
        web_already_running=web_already_running,
        web_auth_enabled=web_auth_enabled,
        probe_bind=probe_web_bind,
        next_available_port=next_available_web_port,
    )
