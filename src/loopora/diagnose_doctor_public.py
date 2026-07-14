from __future__ import annotations

from typing import Any

from loopora.diagnose_doctor_public_actions import (
    PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND as PUBLIC_NEXT_ACTION_SUMMARY_BY_KIND,
    doctor_web_readiness_blockers as doctor_web_readiness_blockers,
    project_public_doctor_next_action_contract as _project_public_doctor_next_action_contract,
    public_next_action_kind as _public_next_action_kind,
    public_next_action_summaries as _public_next_action_summaries,
    public_next_actions as _public_next_actions,
    public_readiness_axes as _public_readiness_axes,
    public_web_readiness_blockers as _public_web_readiness_blockers,
    public_web_recovery_action as public_web_recovery_action,
    public_web_recovery_actions as _public_web_recovery_actions,
)
from loopora.diagnose_doctor_projection import (
    first_task_handoff_policy_summary,
    first_task_message_example_state,
)

DOCTOR_PUBLIC_SCHEMA_VERSION = 2


def doctor_public_json_payload(report: dict[str, Any]) -> dict[str, Any]:
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
    web = report.get("web") if isinstance(report.get("web"), dict) else {}
    project_directory = report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
    entries = [entry for entry in list(report.get("agent_entries") or []) if isinstance(entry, dict)]
    next_actions = _public_next_actions(report)
    project_directory_status = _public_optional_text(project_directory.get("status")) or "unknown"
    target_project_required = project_directory_status in {"required", "not_directory", "unavailable"}
    payload = {
        "schema_version": DOCTOR_PUBLIC_SCHEMA_VERSION,
        "doctor_schema_version": report.get("schema_version"),
        "redacted": True,
        "status": report.get("status"),
        "ready": report.get("ready"),
        "agent_entry_ready": report.get("agent_entry_ready"),
        "strict_ready": report.get("strict_ready"),
        "target_project_required": target_project_required,
        "project_directory_status": project_directory_status,
        "package": {
            "name": package.get("name"),
            "version": package.get("version"),
            "source_revision": package.get("source_revision"),
            "source_tree_status": package.get("source_tree_status"),
            "python": package.get("python"),
        },
        "environment": _public_environment_report(package),
        "app_state": {
            "status": app_state.get("status"),
            "schema_version": app_state.get("schema_version"),
            "current_schema_version": app_state.get("current_schema_version"),
            "web_ready": app_state.get("web_ready"),
            "needs_attention": app_state.get("needs_attention"),
            "next_action": app_state.get("next_action"),
        },
        "web": {
            "default": web.get("default"),
            "loopback": web.get("loopback"),
            "requires_token_when_non_loopback": web.get("requires_token_when_non_loopback"),
            "start_available": web.get("start_available"),
            "start_blocked_reason": _public_optional_text(web.get("start_blocked_reason")),
            "readiness_blockers": _public_web_readiness_blockers(web),
            "recovery_actions": _public_web_recovery_actions(web),
            "recovery_action": public_web_recovery_action(web),
            "alternate_port_available": bool(web.get("suggested_port")),
        },
        "agent_entries": [_public_agent_entry(entry) for entry in entries],
        "ready_adapter_count": report.get("ready_adapter_count"),
        "attention_adapter_count": report.get("attention_adapter_count"),
        "recommended_adapter": report.get("recommended_adapter"),
        "first_task_guidance_available": bool(str(report.get("first_task_message_example") or "").strip()),
        "first_task_message_example_state": first_task_message_example_state(report),
        "first_task_handoff_policy": _public_first_task_handoff_policy(report),
        "first_task_handoff_executable": bool(report.get("first_task_handoff_executable")),
        "first_task_handoff_blockers": list(report.get("first_task_handoff_blockers") or []),
        "primary_next_action_kind": next_actions[0] if next_actions else "",
        "next_action_kinds": next_actions,
        "next_actions": next_actions,
        "next_action_summaries": _public_next_action_summaries(next_actions),
    }
    _project_public_doctor_next_action_contract(payload, report=report)
    payload["readiness_axes"] = _public_readiness_axes(payload)
    return {"diagnose_doctor_public_summary": doctor_public_summary(payload), **payload}


def doctor_public_summary(payload: dict[str, Any]) -> dict[str, Any]:
    app_state = payload.get("app_state") if isinstance(payload.get("app_state"), dict) else {}
    web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
    return {
        "schema_version": payload.get("schema_version"),
        "doctor_schema_version": payload.get("doctor_schema_version"),
        "status": payload.get("status"),
        "ready": payload.get("ready"),
        "agent_entry_ready": payload.get("agent_entry_ready"),
        "strict_ready": payload.get("strict_ready"),
        "target_project_required": payload.get("target_project_required"),
        "redacted": payload.get("redacted"),
        "environment": payload.get("environment"),
        "project_directory_status": payload.get("project_directory_status"),
        "ready_adapter_count": payload.get("ready_adapter_count"),
        "attention_adapter_count": payload.get("attention_adapter_count"),
        "recommended_adapter": payload.get("recommended_adapter"),
        "first_task_guidance_available": payload.get("first_task_guidance_available"),
        "first_task_message_example_state": payload.get("first_task_message_example_state"),
        "first_task_handoff_policy": payload.get("first_task_handoff_policy"),
        "first_task_handoff_executable": payload.get("first_task_handoff_executable"),
        "first_task_handoff_blockers": payload.get("first_task_handoff_blockers"),
        "primary_next_action_kind": payload.get("primary_next_action_kind"),
        "app_state_status": app_state.get("status"),
        "app_state_web_ready": app_state.get("web_ready"),
        "web_start_available": web.get("start_available"),
        "web_start_blocked_reason": _public_optional_text(web.get("start_blocked_reason")),
        "web_readiness_blockers": list(web.get("readiness_blockers") or []),
        "web_recovery_actions": list(web.get("recovery_actions") or []),
        "web_recovery_action": _public_optional_text(web.get("recovery_action")),
        "readiness_axes": payload.get("readiness_axes"),
        "next_action_kinds": payload.get("next_action_kinds"),
        "next_actions": payload.get("next_actions"),
        "next_action_summaries": payload.get("next_action_summaries"),
        "next_action_ready_kinds": payload.get("next_action_ready_kinds"),
        "next_action_ready_now_kinds": payload.get("next_action_ready_now_kinds"),
        "next_action_ready_after_actions": payload.get("next_action_ready_after_actions"),
        "next_action_blocked_kinds": payload.get("next_action_blocked_kinds"),
        "next_action_command_blockers": payload.get("next_action_command_blockers"),
    }


def _public_first_task_handoff_policy(report: dict[str, Any]) -> dict[str, str]:
    policy = first_task_handoff_policy_summary(report)
    return {
        key: policy[key]
        for key in ("preferred_source", "fallback_source")
        if policy.get(key)
    }


def _public_optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _public_environment_report(package: dict[str, Any]) -> dict[str, str | None]:
    return {
        "os": _public_optional_text(package.get("os")),
        "machine": _public_optional_text(package.get("machine")),
        "python": _public_optional_text(package.get("python")),
        "python_implementation": _public_optional_text(package.get("python_implementation")),
    }


def _public_agent_entry(entry: dict[str, Any]) -> dict[str, Any]:
    failed_checks = [item for item in list(entry.get("failed_checks") or []) if isinstance(item, dict)]
    return {
        "adapter": entry.get("adapter"),
        "label": entry.get("label"),
        "ready": entry.get("ready"),
        "check_status": entry.get("check_status"),
        "install_state": _public_next_action_kind(str(entry.get("install_state") or "")),
        "details_are_expected": entry.get("details_are_expected"),
        "next_action": _public_next_action_kind(str(entry.get("next_action") or "")),
        "failed_check_names": [str(item.get("name") or "").strip() for item in failed_checks if item.get("name")],
    }
