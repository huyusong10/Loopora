from __future__ import annotations

from typing import Any

from loopora.app_state_readiness import app_state_web_readiness_blockers
from loopora.diagnose_doctor_projection import next_action_kinds, structured_next_actions
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.first_use_web_guidance import WEB_CREATION_CHOICE_SUMMARY

PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND = {
    "check_fit_first": "If task fit is uncertain, run the static fit guide before installing same-Agent project entries.",
    "create_project_directory": "Create the target project directory before installing same-Agent project entries.",
    "blocked_by_project_directory": "Choose a usable project directory before installing same-Agent project entries.",
    "choose_project_directory": "Choose a usable project directory before installing same-Agent project entries.",
    "install_agent_entry": "Choose the same-Agent project entry that matches the current host, then confirm readiness.",
    "inspect_or_repair_agent_entry": "Inspect or repair the installed same-Agent project entry before planning.",
    "create_recovery_archive": (
        "Create and inspect a private recovery archive before applying any local App-state reset."
    ),
    "preview_app_database_reset": "Local App/Web state needs attention; preview reset scope before applying changes.",
    "use_matching_loopora_version_or_reset": (
        "Use a matching or newer Loopora version, or preview an app-scope reset before retrying Web start."
    ),
    "inspect_or_reset_app_state": "Inspect or reset local App state before retrying Web start.",
    "use_temporary_app_home": (
        "Start Web with a temporary empty App home for preview or troubleshooting without changing blocked local App state."
    ),
    "confirm_readiness": "Repeat the read-only readiness check before returning to the Agent.",
    "return_to_agent": (
        "Return to the Agent with the Loopora fit reason, task goal, fake-done risk, required evidence, "
        "judgment tradeoffs, and optional direct-path context."
    ),
    "refresh_agent_host": "Refresh or restart the Agent host if project entries are not visible.",
    "confirm_agent_visibility": "Confirm the Agent host can see the project entries before planning.",
    "run_loopora_plan": "Use the Agent planning step to prepare a reviewable Loop preview.",
    "review_ready_loop_preview": "Review whether the READY Loop preview matches the task judgment.",
    "run_loopora_run": "Use the Agent run step only after the preview matches the task judgment.",
    "support": "Open usage/setup support guidance for redacted public reporting.",
    "start_web": f"Start Fit Guide/Web choices in Web after readiness for {WEB_CREATION_CHOICE_SUMMARY}.",
    "configure_web_auth": "Configure Web authentication or an explicit unsafe opt-in before network Web starts.",
    "resolve_web_port": "Choose a free Web port or stop the service using the configured port.",
    "resolve_web_bind": "Choose a different Web bind host or port.",
}


def doctor_web_readiness_blockers(app_state: dict[str, Any], web: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = app_state_web_readiness_blockers(app_state)
    reason = str(web.get("start_blocked_reason") or "").strip()
    if reason:
        blockers.append({"kind": reason, "recovery_action": public_web_recovery_action(web)})
    return blockers


def public_web_recovery_action(web: dict[str, Any]) -> str:
    actions = public_web_recovery_actions(web)
    if len(actions) > 1:
        return "multiple_actions_required"
    return actions[0] if actions else ""


def project_public_doctor_next_action_contract(payload: dict[str, Any], *, report: dict[str, Any]) -> None:
    actions = _public_readiness_actions(report)
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)


def public_readiness_axes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    app_state = payload.get("app_state") if isinstance(payload.get("app_state"), dict) else {}
    web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
    project_status = _public_optional_text(payload.get("project_directory_status")) or "unknown"
    web_blockers = [
        str(item.get("kind") or "unknown").strip() or "unknown"
        for item in list(web.get("readiness_blockers") or [])
        if isinstance(item, dict)
    ]
    web_start_available = web.get("start_available")
    web_ready = web_start_available is True and not web_blockers
    web_status = "available" if web_ready else "blocked" if web_start_available is not None or web_blockers else "unknown"
    first_task_handoff_executable = bool(payload.get("first_task_handoff_executable"))
    first_task_handoff_blockers = [
        str(blocker).strip() for blocker in list(payload.get("first_task_handoff_blockers") or []) if str(blocker).strip()
    ]
    app_needs_attention = app_state.get("needs_attention") is True
    return [
        {
            "axis": "project_directory",
            "status": project_status,
            "ready": project_status == "ready",
            "needs_attention": project_status != "ready",
        },
        {
            "axis": "same_agent_entry",
            "status": "ready" if payload.get("agent_entry_ready") is True else "not_ready",
            "ready": payload.get("agent_entry_ready") is True,
            "ready_adapter_count": payload.get("ready_adapter_count"),
            "attention_adapter_count": payload.get("attention_adapter_count"),
        },
        {
            "axis": "app_state",
            "status": _public_optional_text(app_state.get("status")) or "unknown",
            "ready": not app_needs_attention,
            "needs_attention": app_needs_attention,
        },
        {
            "axis": "web_start",
            "status": web_status,
            "ready": web_ready,
            "blockers": web_blockers,
            "recovery_actions": list(web.get("recovery_actions") or []),
            "recovery_action": _public_optional_text(web.get("recovery_action")) or "inspect_readiness",
        },
        {
            "axis": "first_task_handoff",
            "status": "ready" if first_task_handoff_executable else "blocked",
            "ready": first_task_handoff_executable,
            "blockers": first_task_handoff_blockers,
        },
    ]


def public_web_recovery_actions(web: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for item in list(web.get("readiness_blockers") or []):
        if not isinstance(item, dict):
            continue
        action = _public_optional_text(item.get("recovery_action"))
        if action and action not in actions:
            actions.append(action)
    if actions:
        return actions
    recovery_action = _public_base_web_recovery_action(web)
    return [recovery_action] if recovery_action else []


def public_web_readiness_blockers(web: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for item in list(web.get("readiness_blockers") or []):
        if not isinstance(item, dict):
            continue
        blocker = {
            "kind": _public_optional_text(item.get("kind")) or "unknown",
            "recovery_action": _public_optional_text(item.get("recovery_action")) or "inspect_readiness",
        }
        status = _public_optional_text(item.get("status"))
        if status:
            blocker["status"] = status
        blockers.append(blocker)
    return blockers


def public_next_actions(report: dict[str, Any]) -> list[str]:
    app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
    action_kinds = next_action_kinds(report)
    if action_kinds:
        return [public_next_action_kind(kind, app_state=app_state) for kind in action_kinds]
    actions: list[str] = []
    workdir_state = report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
    project_directory_status = str(workdir_state.get("status") or "").strip()
    if project_directory_status == "missing":
        return ["create_project_directory", "confirm_readiness", "support"]
    if project_directory_status in {"required", "not_directory", "unavailable"}:
        return ["choose_project_directory", "confirm_readiness", "support"]
    app_reset_needed = app_state.get("web_ready") is False
    entries = [entry for entry in list(report.get("agent_entries") or []) if isinstance(entry, dict)]
    if any(entry.get("ready") for entry in entries):
        if app_reset_needed:
            actions.append("create_recovery_archive")
            actions.append(_public_app_state_next_action(app_state))
        actions.extend(["return_to_agent", "confirm_agent_visibility", "run_loopora_plan", "support"])
    else:
        actions.append("check_fit_first")
        actions.append("install_agent_entry")
        if app_reset_needed:
            actions.append("create_recovery_archive")
            actions.append(_public_app_state_next_action(app_state))
        actions.extend(["confirm_readiness", "run_loopora_plan", "support"])
    return actions


def public_next_action_summaries(action_kinds: list[str]) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    for index, kind in enumerate(action_kinds):
        summary = _public_next_action_summary(kind, prior_action_kinds=action_kinds[:index])
        summaries.append({"kind": kind, "summary": summary})
    return summaries


def public_next_action_kind(kind: str, *, app_state: dict[str, Any] | None = None) -> str:
    if kind == "create_workdir":
        return "create_project_directory"
    if kind == "blocked_by_workdir":
        return "blocked_by_project_directory"
    if kind == "choose_workdir":
        return "choose_project_directory"
    if kind == "preview_app_database_reset":
        return _public_app_state_next_action(app_state or {})
    return kind


def _public_readiness_actions(report: dict[str, Any]) -> list[dict[str, Any]]:
    app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
    actions = []
    for action in structured_next_actions(report):
        kind = public_next_action_kind(str(action.get("kind") or ""), app_state=app_state)
        if not kind:
            continue
        projected = {
            "kind": kind,
            "command_ready": action.get("command_ready"),
            "command_blockers": list(action.get("command_blockers") or []),
        }
        after_action = str(action.get("after_action") or "").strip()
        if after_action:
            projected["after_action"] = public_next_action_kind(after_action, app_state=app_state)
        actions.append(projected)
    if actions:
        return actions
    return [{"kind": kind} for kind in public_next_actions(report)]


def _public_optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _public_base_web_recovery_action(web: dict[str, Any]) -> str:
    app_state_recovery = _web_readiness_blocker_recovery_action(web, kind="app_state_not_ready")
    recovery_action = ""
    if app_state_recovery:
        recovery_action = app_state_recovery
    elif web.get("start_available") is True:
        recovery_action = "start_web_after_readiness"
    else:
        reason = str(web.get("start_blocked_reason") or "").strip()
        if reason == "auth_required":
            recovery_action = "set_auth_token_or_explicit_unsafe_opt_in"
        elif reason == "port_in_use" and web.get("suggested_port"):
            recovery_action = "use_suggested_free_port_or_choose_another_port"
        elif reason == "port_in_use":
            recovery_action = "stop_existing_service_or_choose_another_port"
        elif reason == "bind_failed":
            recovery_action = "choose_different_bind_host_or_port"
        elif reason:
            recovery_action = "inspect_web_start_blocker"
    return recovery_action


def _web_readiness_blocker_recovery_action(web: dict[str, Any], *, kind: str) -> str:
    for item in list(web.get("readiness_blockers") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "").strip() == kind:
            return str(item.get("recovery_action") or "").strip()
    return ""


def _public_next_action_summary(kind: str, *, prior_action_kinds: list[str]) -> str:
    if kind == "confirm_readiness":
        return _public_confirm_readiness_summary(prior_action_kinds)
    if _prior_app_state_recovery(prior_action_kinds):
        summary = _public_after_app_recovery_summary(kind)
        if summary:
            return summary
    summary = PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND.get(kind)
    if summary:
        return summary
    return "Inspect the redacted readiness fields for this action category."


def _public_confirm_readiness_summary(prior_action_kinds: list[str]) -> str:
    if "create_project_directory" in prior_action_kinds:
        summary = "After creating the project directory, repeat the read-only readiness check to continue setup."
    elif any(action in prior_action_kinds for action in ("blocked_by_project_directory", "choose_project_directory")):
        summary = "After choosing a usable project directory, repeat the read-only readiness check to continue setup."
    elif "preview_app_database_reset" in prior_action_kinds:
        summary = "After applying an acceptable App reset, repeat the read-only readiness check before continuing."
    elif "use_matching_loopora_version_or_reset" in prior_action_kinds:
        summary = (
            "After using a matching or newer Loopora version, or applying an acceptable App reset, repeat the "
            "read-only readiness check before continuing."
        )
    elif "inspect_or_reset_app_state" in prior_action_kinds:
        summary = "After inspecting or resetting local App state, repeat the read-only readiness check before continuing."
    elif "install_agent_entry" in prior_action_kinds:
        summary = (
            "After installing the matching same-Agent project entry, repeat the read-only readiness check before "
            "returning to the Agent."
        )
    else:
        summary = PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND.get("confirm_readiness", "")
    return summary


def _public_after_app_recovery_summary(kind: str) -> str:
    summaries = {
        "configure_web_auth": (
            "After App readiness is recovered, configure Web authentication or an explicit unsafe opt-in before "
            "network Web starts."
        ),
        "resolve_web_port": (
            "After App readiness is recovered, choose a free Web port or stop the service using the configured port."
        ),
        "resolve_web_bind": "After App readiness is recovered, choose a different Web bind host or port.",
        "start_web": f"After App readiness is recovered, start Fit Guide/Web choices in Web for {WEB_CREATION_CHOICE_SUMMARY}.",
    }
    return summaries.get(kind, "")


def _public_app_state_next_action(app_state: dict[str, Any]) -> str:
    next_action = str(app_state.get("next_action") or "").strip()
    if next_action in {"use_matching_loopora_version_or_reset", "inspect_or_reset_app_state"}:
        return next_action
    return "preview_app_database_reset"


def _prior_app_state_recovery(prior_action_kinds: list[str]) -> bool:
    return any(
        action in prior_action_kinds
        for action in ("preview_app_database_reset", "use_matching_loopora_version_or_reset", "inspect_or_reset_app_state")
    )
