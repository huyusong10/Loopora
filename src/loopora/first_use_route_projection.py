from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from loopora.first_use_action_readiness import (
    first_use_action_by_kind,
    first_use_action_readiness_summary,
    first_use_actions,
    project_first_use_action_readiness_summary,
)
from loopora.first_use_web_recovery import (
    first_use_app_state_readiness_blocker_kinds,
    first_use_web_creation_choice_blockers,
)

FIRST_USE_ROUTE_ACTION_KEYS = ("route_actions_after_strong_fit", "next_actions")
FIRST_USE_COMMAND_ACTION_KINDS = {
    "check_fit_first",
    "open_web_creation_choices",
    "install_agent_entry",
    "confirm_readiness",
    "return_to_agent",
    "run_after_review",
    "support",
    "create_recovery_archive",
    "preview_app_database_reset",
    "use_matching_loopora_version_or_reset",
    "inspect_or_reset_app_state",
    "inspect_app_state",
}
FIRST_USE_SETUP_INDEPENDENT_ACTIONS = {
    "check_fit_first",
    "create_recovery_archive",
    "preview_app_database_reset",
    "use_matching_loopora_version_or_reset",
    "inspect_or_reset_app_state",
    "inspect_app_state",
}
FIRST_USE_FIT_REVIEW_INDEPENDENT_ACTIONS = {
    *FIRST_USE_SETUP_INDEPENDENT_ACTIONS,
    "support",
}
FIRST_USE_SUPPORT_INHERITED_SETUP_BLOCKERS = {"target_project_required"}


@dataclass(frozen=True)
class FirstUseRouteReadinessGate:
    setup_ready: bool
    setup_blockers: list[str]
    fit_review_required: bool
    first_task_ready: bool
    app_state_blockers: list[str]


def project_first_use_route_action_readiness(payload: dict[str, object]) -> None:
    setup_ready = bool(payload.get("setup_commands_ready"))
    setup_blockers = [str(item) for item in list(payload.get("setup_command_blockers") or []) if str(item)]
    fit_review_required = bool(payload.get("fit_review_recommended_before_setup") and setup_ready)
    primary_state = payload.get("primary_first_task_message_state")
    first_task_ready = bool(primary_state.get("ready")) if isinstance(primary_state, dict) else False
    app_state_blockers = first_use_app_state_command_blockers(payload)
    gate = FirstUseRouteReadinessGate(
        setup_ready=setup_ready,
        setup_blockers=setup_blockers,
        fit_review_required=fit_review_required,
        first_task_ready=first_task_ready,
        app_state_blockers=app_state_blockers,
    )
    for key in FIRST_USE_ROUTE_ACTION_KEYS:
        payload[key] = [
            first_use_route_action_with_readiness(
                action,
                gate=gate,
            )
            for action in first_use_actions(payload, key)
        ]


def project_first_use_route_readiness_summary(payload: dict[str, object], *, summary_key: str) -> None:
    route_actions = first_use_actions(payload, "route_actions_after_strong_fit")
    next_actions = first_use_actions(payload, "next_actions")
    route_summary = first_use_action_readiness_summary(route_actions)
    next_summary = first_use_action_readiness_summary(next_actions)
    project_first_use_action_readiness_summary(payload, prefix="route_action", readiness=route_summary)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=next_summary)
    summary = payload.get(summary_key)
    if not isinstance(summary, dict):
        return
    project_first_use_action_readiness_summary(summary, prefix="route_action", readiness=route_summary)
    project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=next_summary)
    web_action = first_use_action_by_kind(route_actions, "open_web_creation_choices")
    if web_action:
        summary["web_route_command_ready"] = web_action.get("command_ready") is not False
        summary["web_route_command_blockers"] = list(web_action.get("command_blockers") or [])
        summary["web_route_preflight_status"] = str(web_action.get("preflight_status") or "not_checked")
        summary["web_route_port"] = web_action.get("port")
        summary["web_route_requested_port"] = web_action.get("requested_port")
        summary["web_route_suggested_port"] = web_action.get("suggested_port")
        summary["web_route_readiness_blockers"] = list(web_action.get("readiness_blockers") or [])


def project_first_use_reviewed_setup_gate(payload: dict[str, object], *, summary_key: str) -> None:
    blockers = first_use_reviewed_setup_gate_blockers(payload)
    ready = bool(payload.get("setup_commands_ready")) and not blockers
    payload["setup_gate_ready"] = ready
    payload["setup_gate_blockers"] = blockers
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        summary["setup_gate_ready"] = ready
        summary["setup_gate_blockers"] = list(blockers)


def first_use_reviewed_setup_gate_blockers(payload: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    if bool(payload.get("fit_review_recommended_before_setup")):
        blockers.append("fit_review_required")
    blockers.extend(str(item) for item in list(payload.get("setup_command_blockers") or []) if str(item))
    return list(dict.fromkeys(blockers))


def first_use_route_action_with_readiness(
    action: dict[str, object],
    *,
    gate: FirstUseRouteReadinessGate,
) -> dict[str, object]:
    projected = dict(action)
    kind = str(projected.get("kind") or "")
    if kind not in FIRST_USE_COMMAND_ACTION_KINDS:
        return projected
    blockers = first_use_route_command_blockers(
        projected,
        kind=kind,
        gate=gate,
    )
    blockers = list(dict.fromkeys(blockers))
    if kind == "install_agent_entry" and isinstance(projected.get("adapter_choices"), list):
        project_first_use_same_agent_setup_readiness(projected, blockers=blockers)
        return projected
    projected["command_ready"] = not blockers
    projected["command_blockers"] = blockers
    projected["action_ready"] = projected["command_ready"]
    projected["action_blockers"] = list(blockers)
    project_first_use_adapter_choices(projected, blockers=blockers)
    return projected


def first_use_route_command_blockers(
    projected: dict[str, object],
    *,
    kind: str,
    gate: FirstUseRouteReadinessGate,
) -> list[str]:
    setup_independent = projected.get("setup_independent") is True
    blockers = (
        []
        if gate.setup_ready or setup_independent or kind in FIRST_USE_SETUP_INDEPENDENT_ACTIONS
        else first_use_inherited_setup_blockers(kind, gate)
    )
    if gate.fit_review_required and not setup_independent and kind not in FIRST_USE_FIT_REVIEW_INDEPENDENT_ACTIONS:
        blockers.append("fit_review_required")
    if kind == "return_to_agent":
        projected["requires_same_agent_entry"] = True
        projected["same_agent_entry_ready"] = False
        projected["requires_first_task_message"] = True
        projected["first_task_message_ready"] = gate.first_task_ready
        blockers.append("same_agent_entry_required")
        blockers.extend(gate.app_state_blockers)
        if not gate.first_task_ready:
            blockers.append("first_task_message_not_ready")
    if kind == "open_web_creation_choices":
        blockers.extend(open_web_creation_choice_blockers(projected))
    if kind == "run_after_review":
        projected["requires_ready_review"] = True
        blockers.extend(gate.app_state_blockers)
        blockers.append("ready_review_required")
    return blockers


def first_use_inherited_setup_blockers(kind: str, gate: FirstUseRouteReadinessGate) -> list[str]:
    if kind == "support":
        return [
            blocker
            for blocker in gate.setup_blockers
            if blocker in FIRST_USE_SUPPORT_INHERITED_SETUP_BLOCKERS
        ]
    return list(gate.setup_blockers)


def open_web_creation_choice_blockers(projected: Mapping[str, object]) -> list[str]:
    return first_use_web_creation_choice_blockers(projected)


def first_use_app_state_command_blockers(payload: Mapping[str, object]) -> list[str]:
    web_route = payload.get("web_route_preflight")
    blockers = list(first_use_app_state_readiness_blocker_kinds(web_route if isinstance(web_route, Mapping) else {}))
    if blockers:
        return blockers
    for key in FIRST_USE_ROUTE_ACTION_KEYS:
        web_action = first_use_action_by_kind(first_use_actions(payload, key), "open_web_creation_choices")
        blockers.extend(first_use_app_state_readiness_blocker_kinds(web_action))
    return list(dict.fromkeys(blockers))


def project_first_use_adapter_choices(projected: dict[str, object], *, blockers: list[str]) -> None:
    if not isinstance(projected.get("adapter_choices"), list):
        return
    projected["adapter_choices"] = [
        {**choice, "command_ready": projected["command_ready"], "command_blockers": list(blockers)}
        for choice in projected["adapter_choices"]
        if isinstance(choice, dict)
    ]


def project_first_use_same_agent_setup_readiness(projected: dict[str, object], *, blockers: list[str]) -> None:
    choices = [choice for choice in list(projected.get("adapter_choices") or []) if isinstance(choice, dict)]
    projected["adapter_choices"] = [
        {**choice, "command_ready": not blockers, "command_blockers": list(blockers)}
        for choice in choices
    ]
    detection = projected.get("current_agent_host") if isinstance(projected.get("current_agent_host"), Mapping) else {}
    command_blockers = list(blockers)
    if not str(projected.get("command") or "").strip():
        command_blockers.extend(str(item) for item in list(detection.get("command_blockers") or []) if str(item))
    command_blockers = list(dict.fromkeys(command_blockers))
    projected["command_ready"] = bool(str(projected.get("command") or "").strip()) and not command_blockers
    projected["command_blockers"] = command_blockers
    ready_choices = [
        choice
        for choice in projected["adapter_choices"]
        if choice.get("fallback_applicable") is True and choice.get("command_ready") is True
    ]
    projected["ready_adapter_choice_count"] = len(ready_choices)
    projected["action_ready"] = projected["command_ready"] or bool(ready_choices)
    projected["action_blockers"] = [] if projected["action_ready"] else list(blockers or command_blockers)
