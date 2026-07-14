from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import DEFAULT_LOOPORA_CLI_ENTRY
from loopora.fit_guidance import FIT_FIRST_TASK_MESSAGE_STATUS, fit_guidance_payload, normalize_fit_guidance_language
from loopora.first_use_review_actions import (
    fit_review_web_actions,
    project_fit_review_action_summary,
)
from loopora.start_guidance_actions import (
    _action_kinds,
    _actions,
    _fit_review_blocks_setup_routes,
    _start_fit_review_allows_setup_routes,
    _start_projected_workdir_state,
    _start_route_actions,
    _start_route_actions_for_review,
    _start_route_workdir_text,
    _start_setup_command_blockers,
    _start_web_route_context,
    _start_workdir_arg,
    _start_workdir_text,
)
from loopora.start_guidance_next_actions import (
    _start_next_actions,
    _truthy_review_input,
)
from loopora.start_guidance_projection import (
    _project_fit_guidance_for_start,
    _project_start_command_field_boundary,
    _project_start_direct_path_action_readiness,
    _project_start_reviewed_setup_gate,
    _project_start_route_action_readiness,
    _project_start_route_readiness_summary,
)
from loopora import start_guidance_constants as _start_constants

START_GUIDANCE_SCHEMA_VERSION = _start_constants.START_GUIDANCE_SCHEMA_VERSION
START_HELP_EPILOG = _start_constants.START_HELP_EPILOG
START_WORKDIR_PLACEHOLDER = _start_constants.START_WORKDIR_PLACEHOLDER


def start_guidance_payload(
    review_inputs: Mapping[str, object] | None = None,
    *,
    workdir: Path | str | None = None,
    language: str = "en",
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    preflight_web_route: bool = False,
) -> dict[str, object]:
    normalized_language = normalize_fit_guidance_language(language)
    inputs = dict(review_inputs or {})
    raw_fit_payload = fit_guidance_payload(
        str(inputs.get("task") or "").strip(),
        loopora_fit_reason=str(inputs.get("fit_reason") or "").strip(),
        fake_done_risks=str(inputs.get("fake_done") or "").strip(),
        required_evidence=str(inputs.get("evidence") or "").strip(),
        judgment_tradeoffs=str(inputs.get("tradeoffs") or "").strip(),
        direct_path_check=str(inputs.get("direct_path") or "").strip(),
        prefer_direct=_truthy_review_input(inputs.get("prefer_direct")),
        language=normalized_language,
        cli_entry=cli_entry,
        workdir=workdir,
    )
    projected_workdir_state = _start_projected_workdir_state(workdir)
    workdir_state = projected_workdir_state if workdir is not None else {}
    workdir_text = _start_workdir_text(workdir, workdir_state)
    workdir_arg, current_agent_host = (
        _start_workdir_arg(_start_route_workdir_text(workdir_text, workdir_state)),
        raw_fit_payload.get("current_agent_host") if isinstance(raw_fit_payload.get("current_agent_host"), Mapping) else {},
    )
    web_route = _start_web_route_context(
        workdir_state,
        workdir_arg=workdir_arg,
        enabled=preflight_web_route,
    )
    route_actions = _start_route_actions(
        workdir_arg=workdir_arg,
        language=normalized_language,
        cli_entry=cli_entry,
        web_route=web_route,
        current_agent_host=current_agent_host,
    )
    workdir_ready = bool(workdir_state) and str(workdir_state.get("status") or "") == "ready"
    task_review = raw_fit_payload.get("task_fit_review") if isinstance(raw_fit_payload.get("task_fit_review"), dict) else {}
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review.get("task_fit_review_summary"), dict) else {}
    fit_setup_blocker = str(summary.get("setup_blocker") or "")
    if _fit_review_blocks_setup_routes(fit_setup_blocker):
        route_actions = []
    task_review_status = str(raw_fit_payload.get("primary_first_task_message_status") or "")
    task_review_supplied = bool(task_review)
    fit_review_recommended_before_setup = not task_review_supplied
    fit_setup_allowed = (not task_review_supplied) or _start_fit_review_allows_setup_routes(summary)
    route_actions = _start_route_actions_for_review(
        route_actions,
        task_review_supplied=task_review_supplied,
        fit_setup_allowed=fit_setup_allowed,
    )
    route_commands_are_placeholders = workdir_arg == shlex.quote(START_WORKDIR_PLACEHOLDER) and not _fit_review_blocks_setup_routes(fit_setup_blocker)
    target_project_required = route_commands_are_placeholders
    setup_allowed = fit_setup_allowed and workdir_ready
    setup_commands_ready = setup_allowed and not route_commands_are_placeholders
    setup_command_readiness_scope = (
        "target_project_gate_fit_review_not_recorded"
        if fit_review_recommended_before_setup
        else "target_project_and_fit_review"
    )
    setup_command_blockers = _start_setup_command_blockers(
        fit_setup_allowed=fit_setup_allowed,
        fit_setup_blocker=fit_setup_blocker,
        task_review_supplied=task_review_supplied,
        route_commands_are_placeholders=route_commands_are_placeholders,
        workdir_state=workdir_state,
    )
    setup_command_state = {
        "fit_review_recommended_before_setup": fit_review_recommended_before_setup,
        "target_project_required": target_project_required,
        "route_commands_are_placeholders": route_commands_are_placeholders,
        "setup_commands_ready": setup_commands_ready,
        "setup_command_readiness_scope": setup_command_readiness_scope,
        "setup_command_blockers": setup_command_blockers,
    }
    route_preview_executable = setup_commands_ready
    route_preview_blockers = [] if route_preview_executable else list(setup_command_blockers)
    next_actions = _start_next_actions(
        raw_fit_payload,
        route_actions=route_actions,
        action_state={
            "task_review_supplied": task_review_supplied,
            "fit_setup_allowed": fit_setup_allowed,
            "route_commands_are_placeholders": route_commands_are_placeholders,
            "cli_entry": cli_entry,
            "review_inputs": inputs,
            "web_route": web_route,
        },
        workdir_state=workdir_state,
        language=normalized_language,
    )
    review_actions = _attach_start_review_actions(
        raw_fit_payload,
        route_actions=route_actions,
        task_review_status=task_review_status,
        target_ready=workdir_ready,
        language=normalized_language,
    )
    fit_payload = _project_fit_guidance_for_start(
        raw_fit_payload,
        route_actions=route_actions,
        next_actions=next_actions,
        setup_command_state=setup_command_state,
        web_route=web_route,
    )
    direct_path_actions = _actions(fit_payload, "direct_path_next_actions")
    primary_message_state = fit_payload.get("primary_first_task_message_state")
    primary_message_state_payload = dict(primary_message_state) if isinstance(primary_message_state, Mapping) else {}
    payload: dict[str, object] = {
        "start_guidance_summary": {
            "schema_version": START_GUIDANCE_SCHEMA_VERSION,
            "language": normalized_language,
            "read_only": True,
            "starts_web": False,
            "installs_agent_entry": False,
            "classifies_task": False,
            "command_fields_are_local_only": True,
            "command_fields_public_pasteable": False,
            "workdir_supplied": workdir is not None,
            "workdir_ready": workdir_ready,
            "workdir_state_status": str(projected_workdir_state.get("status") or ""),
            "target_project_required": target_project_required,
            "route_commands_are_placeholders": route_commands_are_placeholders,
            "task_review_supplied": task_review_supplied,
            "task_review_status": task_review_status,
            "fit_review_recommended_before_setup": fit_review_recommended_before_setup,
            "fit_setup_allowed": fit_setup_allowed,
            "setup_allowed": setup_allowed,
            "setup_commands_ready": setup_commands_ready,
            "setup_command_readiness_scope": setup_command_readiness_scope,
            "setup_command_blockers": setup_command_blockers,
            "route_preview_executable": route_preview_executable,
            "route_preview_blockers": route_preview_blockers,
            "current_agent_host_state": str(current_agent_host.get("state") or ""),
            "current_agent_host_adapter": str(current_agent_host.get("adapter") or ""),
            "same_agent_selection_required": current_agent_host.get("selection_required") is True,
            "web_route_preflight_status": web_route["preflight_status"],
            "web_route_port": web_route["port"],
            "web_route_requested_port": web_route["requested_port"],
            "web_route_suggested_port": web_route["suggested_port"],
            "primary_first_task_message_state": primary_message_state_payload,
            "next_action_kinds": _action_kinds(next_actions),
            "review_action_kinds": _action_kinds(review_actions),
            "route_action_kinds": _action_kinds(route_actions),
            "direct_path_next_action_kinds": _action_kinds(direct_path_actions),
        },
        "schema_version": START_GUIDANCE_SCHEMA_VERSION,
        "language": normalized_language,
        "current_agent_host": dict(current_agent_host),
        "command_fields_are_local_only": True,
        "command_fields_public_pasteable": False,
        "workdir": workdir_text,
        "workdir_arg": workdir_arg,
        "workdir_state": projected_workdir_state,
        "target_project_required": target_project_required,
        "route_commands_are_placeholders": route_commands_are_placeholders,
        "fit_guidance": fit_payload,
        "task_review_supplied": task_review_supplied,
        "task_review_status": task_review_status,
        "fit_review_recommended_before_setup": fit_review_recommended_before_setup,
        "fit_setup_allowed": fit_setup_allowed,
        "setup_allowed": setup_allowed,
        "setup_commands_ready": setup_commands_ready,
        "setup_command_readiness_scope": setup_command_readiness_scope,
        "setup_command_blockers": setup_command_blockers,
        "route_preview_executable": route_preview_executable,
        "route_preview_blockers": route_preview_blockers,
        "web_route_preflight": web_route,
        "next_action_kinds": _action_kinds(next_actions),
        "review_action_kinds": _action_kinds(review_actions),
        "route_action_kinds": _action_kinds(route_actions),
        "direct_path_next_action_kinds": _action_kinds(direct_path_actions),
        "route_actions_after_strong_fit": route_actions,
        "review_actions": review_actions,
        "direct_path_next_actions": direct_path_actions,
        "primary_first_task_message": fit_payload.get("primary_first_task_message", ""),
        "primary_first_task_message_source": fit_payload.get("primary_first_task_message_source", ""),
        "primary_first_task_message_status": task_review_status,
        "primary_first_task_message_ready": fit_payload.get("primary_first_task_message_ready", False),
        "primary_first_task_message_copy_allowed": fit_payload.get("primary_first_task_message_copy_allowed", False),
        "primary_first_task_message_state": primary_message_state_payload,
    }
    payload["next_actions"] = next_actions
    _project_start_route_action_readiness(payload)
    project_fit_review_action_summary(payload, summary_key="start_guidance_summary")
    _project_start_reviewed_setup_gate(payload)
    fit_guidance = payload.get("fit_guidance")
    if isinstance(fit_guidance, dict):
        _project_start_route_action_readiness(fit_guidance)
        project_fit_review_action_summary(fit_guidance, summary_key="fit_guidance_summary")
        _project_start_reviewed_setup_gate(fit_guidance)
        _project_start_route_readiness_summary(fit_guidance)
        _project_start_direct_path_action_readiness(fit_guidance)
    _project_start_route_readiness_summary(payload)
    _project_start_direct_path_action_readiness(payload)
    _project_start_command_field_boundary(payload)
    return payload


def start_guidance_lines(payload: Mapping[str, object]) -> list[str]:
    from loopora.start_guidance_output import start_guidance_lines as render_start_guidance_lines

    return render_start_guidance_lines(payload)


def _attach_start_review_actions(
    fit_payload: dict[str, object],
    *,
    route_actions: list[dict[str, object]],
    task_review_status: str,
    target_ready: bool,
    language: str,
) -> list[dict[str, object]]:
    task_review = fit_payload.get("task_fit_review")
    review_inputs = task_review.get("review_inputs") if isinstance(task_review, Mapping) else {}
    actions = fit_review_web_actions(
        route_actions,
        context={
            "review_pending": task_review_status
            in {
                FIT_FIRST_TASK_MESSAGE_STATUS["example"],
                FIT_FIRST_TASK_MESSAGE_STATUS["preview"],
            },
            "target_ready": target_ready,
            "language": language,
            "review_inputs": review_inputs if isinstance(review_inputs, Mapping) else {},
            "workdir": str(fit_payload.get("workdir") or ""),
        },
    )
    fit_payload["review_actions"] = actions
    return actions
