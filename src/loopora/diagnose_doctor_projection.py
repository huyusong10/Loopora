from __future__ import annotations

from typing import Any

from loopora.agent_adapters import adapter_first_task_message_example_state
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)


def doctor_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": report.get("schema_version"),
        "status": report.get("status"),
        "ready": report.get("ready"),
        "agent_entry_ready": report.get("agent_entry_ready"),
        "strict_ready": report.get("strict_ready"),
        "workdir": report.get("workdir"),
        "target_project_required": bool(report.get("target_project_required")),
        "workdir_state_status": (
            report.get("workdir_state") if isinstance(report.get("workdir_state"), dict) else {}
        ).get("status"),
        "ready_adapter_count": report.get("ready_adapter_count"),
        "attention_adapter_count": report.get("attention_adapter_count"),
        "recommended_adapter": report.get("recommended_adapter"),
        "first_task_guidance_available": bool(str(report.get("first_task_message_example") or "").strip()),
        "first_task_message_example_state": first_task_message_example_state(report),
        "first_task_handoff_policy": first_task_handoff_policy_summary(report),
        "first_task_handoff_executable": bool(report.get("first_task_handoff_executable")),
        "first_task_handoff_blockers": list(report.get("first_task_handoff_blockers") or []),
        "primary_next_action_kind": report.get("primary_next_action_kind"),
        "app_state_status": (report.get("app_state") if isinstance(report.get("app_state"), dict) else {}).get("status"),
        "app_state_web_ready": (report.get("app_state") if isinstance(report.get("app_state"), dict) else {}).get(
            "web_ready"
        ),
        "web_origin": (report.get("web") if isinstance(report.get("web"), dict) else {}).get("origin"),
        "web_start_available": (report.get("web") if isinstance(report.get("web"), dict) else {}).get(
            "start_available"
        ),
        "web_start_blocked_reason": (report.get("web") if isinstance(report.get("web"), dict) else {}).get(
            "start_blocked_reason"
        ),
        "web_access_mode": _doctor_web_access_mode(report),
        "web_readiness_blockers": (report.get("web") if isinstance(report.get("web"), dict) else {}).get(
            "readiness_blockers",
            [],
        ),
        "next_action_kinds": next_action_kinds(report),
        "next_steps": report.get("next_steps"),
    }


def _doctor_web_access_mode(report: dict[str, Any]) -> str:
    web = report.get("web") if isinstance(report.get("web"), dict) else {}
    access_mode = str(web.get("access_mode") or "").strip()
    if access_mode:
        return access_mode
    if web.get("already_running") is True:
        return "open_existing"
    if web.get("start_available") is True:
        return "start_or_open"
    return "recovery_required"


def doctor_json_payload(report: dict[str, Any]) -> dict[str, Any]:
    payload = {"diagnose_doctor_summary": doctor_summary(report), **report}
    payload["next_actions"] = structured_next_actions(report)
    project_doctor_next_action_contract(payload, summary_key="diagnose_doctor_summary")
    return payload


def structured_next_actions(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in list(report.get("next_action_items") or []) if isinstance(item, dict)]


def doctor_actions_with_command_readiness(
    actions: list[dict[str, Any]],
    *,
    first_task_handoff_blockers: list[str],
) -> list[dict[str, Any]]:
    return [
        _doctor_action_with_command_readiness(action, first_task_handoff_blockers=first_task_handoff_blockers)
        for action in actions
    ]


def first_task_handoff_executable(
    *,
    workdir_state: dict[str, Any],
    agent_entry_ready: bool,
    app_state: dict[str, Any],
) -> bool:
    return not first_task_handoff_blockers(
        workdir_state=workdir_state,
        agent_entry_ready=agent_entry_ready,
        app_state=app_state,
    )


def first_task_handoff_blockers(
    *,
    workdir_state: dict[str, Any],
    agent_entry_ready: bool,
    app_state: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    workdir_status = str(workdir_state.get("status") or "").strip()
    workdir_usable = workdir_state.get("usable_for_agent_entries") is True
    if not workdir_usable:
        blockers.append("target_project_required" if workdir_status == "required" else "target_project_unready")
    if not agent_entry_ready:
        blockers.append("same_agent_entry_required")
    if workdir_usable and app_state.get("needs_attention") is True:
        blockers.append("app_state_not_ready")
    return blockers


def first_task_message_example_state(report: dict[str, Any]) -> dict[str, object]:
    state = report.get("first_task_message_example_state")
    if isinstance(state, dict):
        return {
            "kind": str(state.get("kind") or "generic_orientation_example").strip(),
            "source": str(state.get("source") or "generic_example").strip(),
            "copy_allowed": bool(state.get("copy_allowed")),
            "completed_review": bool(state.get("completed_review")),
        }
    return adapter_first_task_message_example_state()


def first_task_handoff_policy_summary(report: dict[str, Any]) -> dict[str, str]:
    policy = report.get("first_task_handoff_policy") if isinstance(report.get("first_task_handoff_policy"), dict) else {}
    return {
        key: str(policy.get(key) or "").strip()
        for key in ("preferred_source", "fallback_source", "fit_command", "plan_command", "copy_rule")
        if str(policy.get(key) or "").strip()
    }


def project_doctor_next_action_contract(payload: dict[str, Any], *, summary_key: str) -> None:
    actions = structured_next_actions(payload)
    action_kinds = _action_kinds(actions)
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def next_action_kinds(report: dict[str, Any]) -> list[str]:
    items = [item for item in list(report.get("next_action_items") or []) if isinstance(item, dict)]
    return [str(item.get("kind") or "").strip() for item in items if str(item.get("kind") or "").strip()]


def doctor_action_step(action: dict[str, Any], *, language: str = "en") -> str:
    from loopora.diagnose_doctor_steps import doctor_action_step as render_doctor_action_step

    return render_doctor_action_step(action, language=language)


def next_steps_from_actions(actions: list[dict[str, Any]], *, language: str = "en") -> list[str]:
    from loopora.diagnose_doctor_steps import next_steps_from_actions

    return next_steps_from_actions(actions, language=language)


def _doctor_action_with_command_readiness(
    action: dict[str, Any],
    *,
    first_task_handoff_blockers: list[str],
) -> dict[str, Any]:
    projected = dict(action)
    choices = projected.get("adapter_choices")
    if isinstance(choices, list):
        projected["adapter_choices"] = [
            _doctor_choice_with_command_readiness(choice)
            for choice in choices
            if isinstance(choice, dict)
        ]
    if not _doctor_action_has_command(projected):
        return projected
    blockers = _doctor_action_command_blockers(projected, first_task_handoff_blockers=first_task_handoff_blockers)
    if "command_ready" not in projected:
        projected["command_ready"] = not blockers
    if "command_blockers" not in projected:
        projected["command_blockers"] = blockers
    return projected


def _doctor_choice_with_command_readiness(choice: dict[str, Any]) -> dict[str, Any]:
    projected = dict(choice)
    if _doctor_action_has_command(projected):
        projected.setdefault("command_ready", True)
        projected.setdefault("command_blockers", [])
    return projected


def _doctor_action_has_command(action: dict[str, Any]) -> bool:
    return any(str(action.get(key) or "").strip() for key in ("command", "command_template", "unsafe_command"))


def _doctor_action_command_blockers(
    action: dict[str, Any],
    *,
    first_task_handoff_blockers: list[str],
) -> list[str]:
    existing = [str(blocker).strip() for blocker in list(action.get("command_blockers") or []) if str(blocker).strip()]
    if existing:
        return existing
    kind = str(action.get("kind") or "").strip()
    if kind == "run_loopora_plan":
        return list(first_task_handoff_blockers)
    if kind == "run_loopora_run":
        return ["ready_review_required"]
    return []


def _action_kinds(actions: list[dict[str, Any]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
