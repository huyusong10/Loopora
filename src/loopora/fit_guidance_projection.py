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
from loopora.first_use_review_actions import (
    fit_review_is_pending,
    fit_review_web_actions,
    project_fit_review_action_summary,
)
from loopora.fit_guidance_actions import (
    FIT_COMMAND_FIELD_KEYS,
    FIT_WORKDIR_ARG,
    _fit_default_web_route_context,
    _localized_direct_path_next_actions,
    _localized_fit_next_actions,
)
from loopora.fit_guidance_workdir_actions import (
    _fit_completion_workdir,
    _fit_incomplete_review_recovery_actions,
    _fit_read_only_support_actions,
    _fit_setup_command_blockers,
    _fit_workdir_recovery_actions,
    _merge_review_and_workdir_recovery_actions,
)
from loopora.fit_review_guidance import (
    FIT_REVIEW_SETUP_GATE,
    _fit_review_completion_action,
    _task_fit_review_needs_direct_decision_input,
    _task_fit_review_prefers_direct,
    _task_fit_review_ready_for_plan_message,
    _task_fit_review_ready_for_setup,
)


def _project_fit_command_field_boundary(payload: dict[str, object]) -> None:
    payload["command_fields_are_local_only"] = True
    payload["command_fields_public_pasteable"] = False
    fit_summary = payload.get("fit_guidance_summary")
    if isinstance(fit_summary, dict):
        fit_summary["command_fields_are_local_only"] = True
        fit_summary["command_fields_public_pasteable"] = False
    for key in ("next_actions", "review_actions", "route_actions_after_strong_fit", "direct_path_next_actions"):
        payload[key] = [_action_with_local_command_boundary(action) for action in _fit_actions(payload, key)]


def _action_with_local_command_boundary(action: dict[str, object]) -> dict[str, object]:
    projected = dict(action)
    if _has_command_field(projected):
        projected["local_only"] = True
    choices = projected.get("adapter_choices")
    if isinstance(choices, list):
        projected["adapter_choices"] = [
            _action_with_local_command_boundary(dict(choice))
            for choice in choices
            if isinstance(choice, dict)
        ]
    recovery_actions = projected.get("recovery_actions")
    if isinstance(recovery_actions, list):
        projected["recovery_actions"] = [
            _action_with_local_command_boundary(dict(item))
            for item in recovery_actions
            if isinstance(item, dict)
        ]
    return projected


def _has_command_field(payload: Mapping[str, object]) -> bool:
    return any(str(payload.get(key) or "").strip() for key in FIT_COMMAND_FIELD_KEYS)


def _project_fit_summary_action_kinds(payload: dict[str, object]) -> None:
    next_action_kinds = _fit_action_kinds(_fit_actions(payload, "next_actions"))
    route_action_kinds = _fit_action_kinds(_fit_actions(payload, "route_actions_after_strong_fit"))
    direct_path_next_action_kinds = _fit_action_kinds(_fit_actions(payload, "direct_path_next_actions"))
    payload["next_action_kinds"] = next_action_kinds
    payload["route_action_kinds"] = route_action_kinds
    payload["direct_path_next_action_kinds"] = direct_path_next_action_kinds
    fit_summary = payload.get("fit_guidance_summary")
    if not isinstance(fit_summary, dict):
        return
    fit_summary["next_action_kinds"] = list(next_action_kinds)
    fit_summary["route_action_kinds"] = list(route_action_kinds)
    fit_summary["direct_path_next_action_kinds"] = list(direct_path_next_action_kinds)


def _project_fit_direct_path_action_readiness(payload: dict[str, object]) -> None:
    readiness = first_use_action_readiness_summary(_fit_actions(payload, "direct_path_next_actions"))
    project_first_use_action_readiness_summary(payload, prefix="direct_path_next_action", readiness=readiness)
    fit_summary = payload.get("fit_guidance_summary")
    if isinstance(fit_summary, dict):
        project_first_use_action_readiness_summary(fit_summary, prefix="direct_path_next_action", readiness=readiness)


def _fit_actions(payload: Mapping[str, object], key: str) -> list[dict[str, object]]:
    actions = payload.get(key)
    return [action for action in list(actions or []) if isinstance(action, dict)]


def _fit_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _project_fit_route_action_readiness(payload: dict[str, object]) -> None:
    project_first_use_route_action_readiness(payload)


def _project_fit_route_readiness_summary(payload: dict[str, object]) -> None:
    project_first_use_route_readiness_summary(payload, summary_key="fit_guidance_summary")


def _project_fit_reviewed_setup_gate(payload: dict[str, object]) -> None:
    project_first_use_reviewed_setup_gate(payload, summary_key="fit_guidance_summary")


def _project_fit_review_action_readiness(payload: dict[str, object]) -> None:
    project_fit_review_action_summary(payload, summary_key="fit_guidance_summary")


def _project_fit_task_review_status(payload: dict[str, object]) -> None:
    task_review_supplied = isinstance(payload.get("task_fit_review"), dict)
    task_review_status = str(payload.get("primary_first_task_message_status") or "")
    setup_allowed = bool(payload.get("setup_commands_ready"))
    payload["task_review_supplied"] = task_review_supplied
    payload["task_review_status"] = task_review_status
    payload["setup_allowed"] = setup_allowed
    fit_summary = payload.get("fit_guidance_summary")
    if isinstance(fit_summary, dict):
        fit_summary["task_review_supplied"] = task_review_supplied
        fit_summary["task_review_status"] = task_review_status
        fit_summary["setup_allowed"] = setup_allowed


def _project_fit_guidance_for_workdir(
    payload: dict[str, object],
    *,
    task_review: Mapping[str, object],
    workdir_state: Mapping[str, object],
    projected_workdir_state: Mapping[str, object],
    route_context: Mapping[str, object],
) -> None:
    workdir_arg = str(route_context["workdir_arg"])
    language = str(route_context["language"])
    cli_entry = str(route_context["cli_entry"])
    web_route = route_context.get("web_route") if isinstance(route_context.get("web_route"), Mapping) else None
    current_agent_host = route_context.get("current_agent_host") if isinstance(route_context.get("current_agent_host"), Mapping) else None
    setup_routes_blocked = bool(
        task_review
        and (
            _task_fit_review_prefers_direct(task_review)
            or _task_fit_review_needs_direct_decision_input(task_review)
        )
    )
    target_project_required = workdir_arg == FIT_WORKDIR_ARG and not setup_routes_blocked
    route_commands_are_placeholders = target_project_required
    setup_command_blockers = _fit_setup_command_blockers(
        task_review,
        route_commands_are_placeholders=route_commands_are_placeholders,
        workdir_state=workdir_state,
    )
    fit_review_recommended_before_setup = not bool(task_review)
    setup_command_readiness_scope = (
        "target_project_gate_fit_review_not_recorded"
        if fit_review_recommended_before_setup
        else "target_project_and_fit_review"
    )
    route_preview_executable = not setup_command_blockers
    route_preview_blockers = [] if route_preview_executable else list(setup_command_blockers)
    route_actions = (
        []
        if setup_routes_blocked
        else _localized_fit_next_actions(
            language=language,
            cli_entry=cli_entry,
            workdir_arg=workdir_arg,
            web_route=web_route,
            current_agent_host=current_agent_host,
        )
    )
    payload["route_actions_after_strong_fit"] = route_actions
    review_inputs = task_review.get("review_inputs") if isinstance(task_review.get("review_inputs"), Mapping) else {}
    payload["review_actions"] = fit_review_web_actions(
        route_actions,
        context={
            "review_pending": fit_review_is_pending(task_review),
            "target_ready": bool(workdir_state) and str(workdir_state.get("status") or "") == "ready",
            "language": language,
            "review_inputs": review_inputs,
            "workdir": str(projected_workdir_state.get("workdir") or ""),
        },
    )
    recovery_actions = _fit_workdir_recovery_actions(
        workdir_state,
        cli_entry=cli_entry,
        language=language,
        review_inputs=review_inputs,
    )
    if task_review and _task_fit_review_prefers_direct(task_review):
        payload["next_actions"] = _merge_review_and_workdir_recovery_actions(
            _localized_direct_path_next_actions(language=language, include_record_action=False),
            _fit_read_only_support_actions(
                workdir_state,
                cli_entry=cli_entry,
                language=language,
                web_route=web_route,
            ),
        )
    elif task_review and _task_fit_review_needs_direct_decision_input(task_review):
        payload["next_actions"] = _merge_review_and_workdir_recovery_actions(
            payload["next_actions"],
            _fit_read_only_support_actions(
                workdir_state,
                cli_entry=cli_entry,
                language=language,
                web_route=web_route,
            ),
        )
    elif task_review and not _task_fit_review_ready_for_setup(dict(task_review)):
        payload["next_actions"] = _merge_review_and_workdir_recovery_actions(
            payload["next_actions"],
            _fit_incomplete_review_recovery_actions(
                recovery_actions,
                workdir_state=workdir_state,
                cli_entry=cli_entry,
                language=language,
                web_route=web_route,
            ),
        )
    elif _task_fit_review_ready_for_setup(dict(task_review)):
        payload["next_actions"] = recovery_actions if setup_command_blockers else route_actions
    elif not task_review:
        payload["next_actions"] = (
            recovery_actions
            if setup_command_blockers
            else [
                _fit_review_completion_action(
                    {},
                    language=language,
                    cli_entry=cli_entry,
                    workdir=_fit_completion_workdir(workdir_state),
                )
            ]
        )
    if projected_workdir_state:
        payload["workdir"] = str(projected_workdir_state.get("workdir") or "")
        payload["workdir_arg"] = workdir_arg
        payload["workdir_state"] = dict(projected_workdir_state)
        payload["workdir_ready"] = str(projected_workdir_state.get("status") or "") == "ready"
    payload["web_route_preflight"] = dict(web_route or _fit_default_web_route_context())
    _project_task_fit_review_setup_boundary(
        payload,
        route_preview_executable=route_preview_executable,
        setup_command_blockers=setup_command_blockers,
    )
    payload["target_project_required"] = target_project_required
    payload["route_commands_are_placeholders"] = route_commands_are_placeholders
    payload["setup_commands_ready"] = route_preview_executable
    payload["fit_review_recommended_before_setup"] = fit_review_recommended_before_setup
    payload["setup_command_readiness_scope"] = setup_command_readiness_scope
    payload["setup_command_blockers"] = setup_command_blockers
    payload["route_preview_executable"] = route_preview_executable
    payload["route_preview_blockers"] = route_preview_blockers
    _project_fit_workdir_summary(
        payload,
        workdir_state=projected_workdir_state,
        summary_values={
            "target_project_required": target_project_required,
            "route_commands_are_placeholders": route_commands_are_placeholders,
            "setup_commands_ready": route_preview_executable,
            "fit_review_recommended_before_setup": fit_review_recommended_before_setup,
            "setup_command_readiness_scope": setup_command_readiness_scope,
            "setup_command_blockers": setup_command_blockers,
            "route_preview_executable": route_preview_executable,
            "route_preview_blockers": route_preview_blockers,
        },
    )


def _project_fit_workdir_summary(
    payload: dict[str, object],
    *,
    workdir_state: Mapping[str, object],
    summary_values: Mapping[str, object],
) -> None:
    fit_summary = payload["fit_guidance_summary"]
    if not isinstance(fit_summary, dict):
        return
    fit_summary.update(summary_values)
    fit_summary["web_route_preflight_status"] = payload["web_route_preflight"]["preflight_status"]
    fit_summary["web_route_port"] = payload["web_route_preflight"]["port"]
    fit_summary["web_route_requested_port"] = payload["web_route_preflight"]["requested_port"]
    fit_summary["web_route_suggested_port"] = payload["web_route_preflight"]["suggested_port"]
    if workdir_state:
        fit_summary["workdir_ready"] = str(workdir_state.get("status") or "") == "ready"
        fit_summary["workdir_state_status"] = str(workdir_state.get("status") or "")


def _project_task_fit_review_setup_boundary(
    payload: dict[str, object],
    *,
    route_preview_executable: bool,
    setup_command_blockers: list[str],
) -> None:
    task_review = payload.get("task_fit_review")
    if not isinstance(task_review, dict) or not _task_fit_review_ready_for_plan_message(task_review):
        return
    if _task_fit_review_prefers_direct(task_review) or _task_fit_review_needs_direct_decision_input(task_review):
        return
    summary = task_review.get("task_fit_review_summary")
    if not isinstance(summary, dict):
        return
    blockers = [] if route_preview_executable else list(setup_command_blockers)
    summary["setup_allowed"] = route_preview_executable
    summary["setup_gate"] = FIT_REVIEW_SETUP_GATE["ready"] if route_preview_executable else FIT_REVIEW_SETUP_GATE["target_blocked"]
    summary["setup_blocker"] = "none" if route_preview_executable else (blockers[0] if blockers else "setup_command_blocked")
    summary["setup_command_blockers"] = blockers
