from __future__ import annotations

from collections.abc import Mapping

from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.first_use_route_projection import (
    project_first_use_reviewed_setup_gate,
    project_first_use_route_action_readiness,
    project_first_use_route_readiness_summary,
)
from loopora.start_guidance_actions import _action_kinds, _actions, _copy_route_action
from loopora.start_guidance_constants import START_COMMAND_FIELD_KEYS


def _project_start_command_field_boundary(payload: dict[str, object]) -> None:
    for key in ("next_actions", "review_actions", "route_actions_after_strong_fit", "direct_path_next_actions"):
        payload[key] = [_start_action_with_local_command_boundary(action) for action in _actions(payload, key)]
    fit_guidance = payload.get("fit_guidance")
    if isinstance(fit_guidance, dict):
        _project_start_command_field_boundary(fit_guidance)
    summary = payload.get("start_guidance_summary")
    if isinstance(summary, dict):
        summary["command_fields_are_local_only"] = True
        summary["command_fields_public_pasteable"] = False
    fit_summary = payload.get("fit_guidance_summary")
    if isinstance(fit_summary, dict):
        fit_summary["command_fields_are_local_only"] = True
        fit_summary["command_fields_public_pasteable"] = False


def _start_action_with_local_command_boundary(action: dict[str, object]) -> dict[str, object]:
    projected = dict(action)
    if _start_has_command_field(projected):
        projected["local_only"] = True
    choices = projected.get("adapter_choices")
    if isinstance(choices, list):
        projected["adapter_choices"] = [
            _start_action_with_local_command_boundary(dict(choice))
            for choice in choices
            if isinstance(choice, dict)
        ]
    recovery_actions = projected.get("recovery_actions")
    if isinstance(recovery_actions, list):
        projected["recovery_actions"] = [
            _start_action_with_local_command_boundary(dict(action))
            for action in recovery_actions
            if isinstance(action, dict)
        ]
    return projected


def _start_has_command_field(payload: Mapping[str, object]) -> bool:
    return any(str(payload.get(key) or "").strip() for key in START_COMMAND_FIELD_KEYS)


def _project_start_route_action_readiness(payload: dict[str, object]) -> None:
    project_first_use_route_action_readiness(payload)


def _project_start_route_readiness_summary(payload: dict[str, object]) -> None:
    summary_key = "start_guidance_summary" if "start_guidance_summary" in payload else "fit_guidance_summary"
    project_first_use_route_readiness_summary(payload, summary_key=summary_key)


def _project_start_direct_path_action_readiness(payload: dict[str, object]) -> None:
    summary_key = "start_guidance_summary" if "start_guidance_summary" in payload else "fit_guidance_summary"
    readiness = first_use_action_readiness_summary(_actions(payload, "direct_path_next_actions"))
    project_first_use_action_readiness_summary(payload, prefix="direct_path_next_action", readiness=readiness)
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        project_first_use_action_readiness_summary(summary, prefix="direct_path_next_action", readiness=readiness)


def _project_start_reviewed_setup_gate(payload: dict[str, object]) -> None:
    summary_key = "start_guidance_summary" if "start_guidance_summary" in payload else "fit_guidance_summary"
    project_first_use_reviewed_setup_gate(payload, summary_key=summary_key)


def _project_fit_guidance_for_start(
    fit_payload: Mapping[str, object],
    *,
    route_actions: list[dict[str, object]],
    next_actions: list[dict[str, object]],
    setup_command_state: Mapping[str, object],
    web_route: Mapping[str, object],
) -> dict[str, object]:
    projected = dict(fit_payload)
    summary = dict(projected.get("fit_guidance_summary") or {})
    command_blockers = list(setup_command_state.get("setup_command_blockers") or [])
    for key in ("target_project_required", "route_commands_are_placeholders", "setup_commands_ready"):
        summary[key] = bool(setup_command_state.get(key))
        projected[key] = bool(setup_command_state.get(key))
    for key in ("fit_review_recommended_before_setup", "setup_command_readiness_scope"):
        value = setup_command_state.get(key)
        summary[key] = value
        projected[key] = value
    route_preview_executable = bool(setup_command_state.get("setup_commands_ready"))
    route_preview_blockers = [] if route_preview_executable else list(command_blockers)
    summary["setup_command_blockers"] = command_blockers
    summary["route_preview_executable"] = route_preview_executable
    summary["route_preview_blockers"] = route_preview_blockers
    projected["fit_guidance_summary"] = summary
    projected["setup_command_blockers"] = list(command_blockers)
    projected["route_preview_executable"] = route_preview_executable
    projected["route_preview_blockers"] = list(route_preview_blockers)
    projected["web_route_preflight"] = dict(web_route)
    projected["route_actions_after_strong_fit"] = [_copy_route_action(action) for action in route_actions]
    projected["next_actions"] = [_copy_route_action(action) for action in next_actions]
    projected["review_actions"] = [_copy_route_action(action) for action in _actions(projected, "review_actions")]
    next_action_kinds = _action_kinds(_actions(projected, "next_actions"))
    review_action_kinds = _action_kinds(_actions(projected, "review_actions"))
    route_action_kinds = _action_kinds(_actions(projected, "route_actions_after_strong_fit"))
    direct_path_next_action_kinds = _action_kinds(_actions(projected, "direct_path_next_actions"))
    projected["next_action_kinds"] = next_action_kinds
    projected["review_action_kinds"] = review_action_kinds
    projected["route_action_kinds"] = route_action_kinds
    projected["direct_path_next_action_kinds"] = direct_path_next_action_kinds
    summary["next_action_kinds"] = list(next_action_kinds)
    summary["review_action_kinds"] = list(review_action_kinds)
    summary["route_action_kinds"] = list(route_action_kinds)
    summary["direct_path_next_action_kinds"] = list(direct_path_next_action_kinds)
    return projected
