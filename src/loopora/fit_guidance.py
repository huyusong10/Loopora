from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from loopora import web_bind_preflight as web_bind_preflight
from loopora.agent_adapter_command_prefix import DEFAULT_LOOPORA_CLI_ENTRY, normalize_loopora_cli_entry
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.fit_guidance_actions import (
    FIT_AGENT_ADAPTER_CHOICES,
    FIT_COMMAND_FIELD_KEYS,
    FIT_DIRECT_PATH_NEXT_ACTIONS,
    FIT_NEXT_ACTION_NOTES_ZH,
    FIT_NEXT_ACTIONS,
    FIT_SUPPORT_COMMAND,
    FIT_WEB_CREATION_COMMAND,
    FIT_WEB_HOST,
    FIT_WEB_PORT,
    FIT_WORKDIR_ARG,
    FIT_WORKDIR_PLACEHOLDER,
    _fit_default_web_route_context,
    _fit_web_route_context,
    _localized_direct_path_next_actions,
    _localized_fit_next_actions,
    _next_actions_for_task_fit_review,
)
from loopora.fit_guidance_projection import (
    _project_fit_command_field_boundary,
    _project_fit_direct_path_action_readiness,
    _project_fit_guidance_for_workdir,
    _project_fit_review_action_readiness,
    _project_fit_reviewed_setup_gate,
    _project_fit_route_action_readiness,
    _project_fit_route_readiness_summary,
    _project_fit_summary_action_kinds,
    _project_fit_task_review_status,
)
from loopora.fit_guidance_workdir_actions import (
    _fit_choose_workdir_action,
    _fit_completion_workdir,
    _fit_workdir_arg,
)
from loopora.first_use_same_agent_setup import first_use_current_agent_host
from loopora.fit_review_guidance import (
    FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS,
    FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH,
    FIT_FIRST_TASK_MESSAGE_STATUS,
    FIT_REVIEW_COMPLETION_PLACEHOLDERS,
    FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH,
    FIT_REVIEW_INPUT_FIELDS,
    FIT_REVIEW_SETUP_GATE,
    PREFER_DIRECT_AGENT_OR_CHECK_ITEMS,
    STRONG_FIT_SIGNAL_ITEMS,
    TASK_FIT_REVIEW_QUESTIONS,
    _fit_first_task_message_example,
    _fit_first_task_message_example_state,
    _primary_first_task_message,
    _primary_first_task_message_state,
    _primary_first_task_message_state_payload,
    _project_primary_first_task_message_state,
    _task_fit_review_payload,
    _task_fit_review_prefers_direct,
)

FIT_GUIDANCE_SCHEMA_VERSION = 2
FIT_GUIDANCE_LANGUAGES = ("en", "zh")
FIT_GUIDANCE_LANGUAGE_ERROR = (
    "expected one of: en, zh; accepted aliases include "
    "en-US, en-GB, zh-CN, zh-Hans, cn, english, chinese, 中文"
)

_WEB_BIND_PREFLIGHT_PATCH_TARGET = web_bind_preflight

__all__ = [
    "FIT_AGENT_ADAPTER_CHOICES",
    "FIT_COMMAND_FIELD_KEYS",
    "FIT_DIRECT_PATH_NEXT_ACTIONS",
    "FIT_FIRST_TASK_MESSAGE_STATUS",
    "FIT_GUIDANCE_LANGUAGES",
    "FIT_GUIDANCE_LANGUAGE_ERROR",
    "FIT_GUIDANCE_SCHEMA_VERSION",
    "FIT_NEXT_ACTIONS",
    "FIT_NEXT_ACTION_NOTES_ZH",
    "FIT_REVIEW_SETUP_GATE",
    "FIT_SUPPORT_COMMAND",
    "FIT_WEB_CREATION_COMMAND",
    "FIT_WEB_HOST",
    "FIT_WEB_PORT",
    "FIT_WORKDIR_ARG",
    "FIT_WORKDIR_PLACEHOLDER",
    "fit_guidance_payload",
    "fit_guidance_web_context",
    "normalize_fit_guidance_language",
    "web_bind_preflight",
]


def normalize_fit_guidance_language(value: str | None) -> str:
    normalized = str(value or "en").strip().lower().replace("_", "-")
    aliases = {
        "": "en",
        "en": "en",
        "en-us": "en",
        "en-gb": "en",
        "english": "en",
        "zh": "zh",
        "zh-cn": "zh",
        "zh-hans": "zh",
        "cn": "zh",
        "chinese": "zh",
        "中文": "zh",
    }
    if normalized in aliases:
        return aliases[normalized]
    raise ValueError(FIT_GUIDANCE_LANGUAGE_ERROR)


def _localized_text(items: list[dict[str, str]], *, language: str) -> list[str]:
    text_key = "text_zh" if language == "zh" else "text_en"
    return [item[text_key] for item in items]


def fit_guidance_payload(  # noqa: PLR0913 - public fit payload keeps review fields explicit for CLI/Web callers.
    task_text: str = "",
    *,
    loopora_fit_reason: str = "",
    fake_done_risks: str = "",
    required_evidence: str = "",
    judgment_tradeoffs: str = "",
    direct_path_check: str = "",
    prefer_direct: bool = False,
    language: str = "en",
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    workdir: Path | str | None = None,
    preflight_web_route: bool = False,
) -> dict[str, object]:
    normalized_language = normalize_fit_guidance_language(language)
    normalized_cli_entry = normalize_loopora_cli_entry(cli_entry)
    current_agent_host = first_use_current_agent_host()
    projected_workdir_state = adapter_workdir_state(workdir)
    workdir_state = projected_workdir_state if workdir is not None else {}
    workdir_arg = _fit_workdir_arg(workdir_state)
    completion_workdir = _fit_completion_workdir(workdir_state)
    web_route = _fit_web_route_context(workdir_state, workdir_arg=workdir_arg, enabled=preflight_web_route)
    payload: dict[str, object] = {
        "fit_guidance_summary": {
            "schema_version": FIT_GUIDANCE_SCHEMA_VERSION,
            "language": normalized_language,
            "recommended_path": "use_loopora_when_later_rounds_need_evidence_governance",
            "not_a_classifier": True,
            "strong_fit_signal_count": len(STRONG_FIT_SIGNAL_ITEMS),
            "non_fit_signal_count": len(PREFER_DIRECT_AGENT_OR_CHECK_ITEMS),
            "direct_path_fallback_available": True,
            "workdir_supplied": workdir is not None,
            "current_agent_host_state": str(current_agent_host.get("state") or ""),
            "current_agent_host_adapter": str(current_agent_host.get("adapter") or ""),
            "same_agent_selection_required": current_agent_host.get("selection_required") is True,
        },
        "schema_version": FIT_GUIDANCE_SCHEMA_VERSION,
        "language": normalized_language,
        "current_agent_host": current_agent_host,
        "strong_fit_signals": _localized_text(STRONG_FIT_SIGNAL_ITEMS, language=normalized_language),
        "prefer_direct_agent_or_checks": _localized_text(
            PREFER_DIRECT_AGENT_OR_CHECK_ITEMS,
            language=normalized_language,
        ),
        "strong_fit_signal_items": [dict(item) for item in STRONG_FIT_SIGNAL_ITEMS],
        "prefer_direct_agent_or_check_items": [dict(item) for item in PREFER_DIRECT_AGENT_OR_CHECK_ITEMS],
        "task_review_questions": [dict(item) for item in TASK_FIT_REVIEW_QUESTIONS],
        "fit_review_input_fields": [dict(item) for item in FIT_REVIEW_INPUT_FIELDS],
        "next_actions": _localized_fit_next_actions(
            language=normalized_language,
            cli_entry=normalized_cli_entry,
            workdir_arg=workdir_arg,
            web_route=web_route,
            current_agent_host=current_agent_host,
        ),
        "direct_path_next_actions": _localized_direct_path_next_actions(
            language=normalized_language,
            cli_entry=normalized_cli_entry,
            workdir=completion_workdir,
        ),
        "first_task_message_example": _fit_first_task_message_example(language=normalized_language),
        "first_task_message_example_state": _fit_first_task_message_example_state(),
    }
    task_review = _task_fit_review_payload(
        task_text,
        loopora_fit_reason=loopora_fit_reason,
        fake_done_risks=fake_done_risks,
        required_evidence=required_evidence,
        judgment_tradeoffs=judgment_tradeoffs,
        direct_path_check=direct_path_check,
        prefer_direct=prefer_direct,
        language=normalized_language,
        cli_entry=normalized_cli_entry,
        completion_workdir=completion_workdir,
    )
    if task_review:
        payload["task_fit_review"] = task_review
        review_inputs = task_review.get("review_inputs") if isinstance(task_review.get("review_inputs"), Mapping) else {}
        payload["direct_path_next_actions"] = _localized_direct_path_next_actions(
            language=normalized_language,
            cli_entry=normalized_cli_entry,
            workdir=completion_workdir,
            review_inputs=review_inputs,
            include_record_action=not _task_fit_review_prefers_direct(task_review),
        )
        payload["next_actions"] = _next_actions_for_task_fit_review(
            task_review,
            language=normalized_language,
            cli_entry=normalized_cli_entry,
        )
    _project_fit_guidance_for_workdir(
        payload,
        task_review=task_review,
        workdir_state=workdir_state,
        projected_workdir_state=projected_workdir_state,
        route_context={
            "workdir_arg": workdir_arg,
            "language": normalized_language,
            "cli_entry": normalized_cli_entry,
            "web_route": web_route,
            "current_agent_host": current_agent_host,
        },
    )
    primary_message, primary_message_source = _primary_first_task_message(payload)
    primary_message_status, primary_message_copy_allowed = _primary_first_task_message_state(payload)
    _project_primary_first_task_message_state(
        payload,
        message=primary_message,
        source=primary_message_source,
        status=primary_message_status,
        copy_allowed=primary_message_copy_allowed,
    )
    _project_fit_route_action_readiness(payload)
    _project_fit_route_readiness_summary(payload)
    _project_fit_review_action_readiness(payload)
    _project_fit_reviewed_setup_gate(payload)
    _project_fit_task_review_status(payload)
    _project_fit_summary_action_kinds(payload)
    _project_fit_direct_path_action_readiness(payload)
    _project_fit_command_field_boundary(payload)
    return payload


def fit_guidance_web_context(
    *,
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    workdir: Path | str | None = None,
) -> dict[str, object]:
    normalized_cli_entry = normalize_loopora_cli_entry(cli_entry)
    current_agent_host = first_use_current_agent_host()
    workdir_supplied = workdir is not None and str(workdir).strip() != ""
    projected_workdir_state = adapter_workdir_state(workdir if workdir_supplied else None)
    workdir_state = projected_workdir_state if workdir_supplied else {}
    workdir_arg = _fit_workdir_arg(workdir_state)
    web_route = _fit_default_web_route_context()
    primary_message_state = _primary_first_task_message_state_payload(
        source="not_available_until_review",
        status=FIT_FIRST_TASK_MESSAGE_STATUS["example"],
        copy_allowed=False,
    )
    payload: dict[str, object] = {
        "fit_guidance_summary": {
            "schema_version": FIT_GUIDANCE_SCHEMA_VERSION,
            "language": "en",
            "recommended_path": "use_loopora_when_later_rounds_need_evidence_governance",
            "not_a_classifier": True,
            "strong_fit_signal_count": len(STRONG_FIT_SIGNAL_ITEMS),
            "non_fit_signal_count": len(PREFER_DIRECT_AGENT_OR_CHECK_ITEMS),
            "direct_path_fallback_available": True,
            "workdir_supplied": workdir_supplied,
            "target_project_required": True,
            "route_commands_are_placeholders": True,
            "setup_commands_ready": False,
            "fit_review_recommended_before_setup": True,
            "setup_command_readiness_scope": "target_project_gate_fit_review_not_recorded",
            "setup_command_blockers": ["target_project_required"],
            "route_preview_executable": False,
            "route_preview_blockers": ["target_project_required"],
            "workdir_ready": False,
            "workdir_state_status": str(workdir_state.get("status") or ""),
            "current_agent_host_state": str(current_agent_host.get("state") or ""),
            "current_agent_host_adapter": str(current_agent_host.get("adapter") or ""),
            "same_agent_selection_required": current_agent_host.get("selection_required") is True,
        },
        "schema_version": FIT_GUIDANCE_SCHEMA_VERSION,
        "current_agent_host": current_agent_host,
        "fit_completion_cli_entry": normalized_cli_entry,
        "not_a_classifier": True,
        "strong_fit_signals": [dict(item) for item in STRONG_FIT_SIGNAL_ITEMS],
        "prefer_direct_agent_or_checks": [dict(item) for item in PREFER_DIRECT_AGENT_OR_CHECK_ITEMS],
        "fit_review_input_fields": [dict(item) for item in FIT_REVIEW_INPUT_FIELDS],
        "fit_review_completion_placeholders": dict(FIT_REVIEW_COMPLETION_PLACEHOLDERS),
        "fit_review_completion_placeholders_zh": dict(FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH),
        "fit_direct_decision_completion_placeholders": dict(FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS),
        "fit_direct_decision_completion_placeholders_zh": dict(FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH),
        "fit_review_setup_gate": dict(FIT_REVIEW_SETUP_GATE),
        "fit_first_task_message_status": dict(FIT_FIRST_TASK_MESSAGE_STATUS),
        "primary_first_task_message": "",
        "primary_first_task_message_source": "not_available_until_review",
        "primary_first_task_message_status": FIT_FIRST_TASK_MESSAGE_STATUS["example"],
        "primary_first_task_message_ready": False,
        "primary_first_task_message_copy_allowed": False,
        "primary_first_task_message_state": primary_message_state,
        "first_task_message_example_state": _fit_first_task_message_example_state(),
        "task_review_questions": [dict(item) for item in TASK_FIT_REVIEW_QUESTIONS],
        "target_project_required": True,
        "route_commands_are_placeholders": True,
        "setup_commands_ready": False,
        "fit_review_recommended_before_setup": True,
        "setup_command_readiness_scope": "target_project_gate_fit_review_not_recorded",
        "setup_command_blockers": ["target_project_required"],
        "route_preview_executable": False,
        "route_preview_blockers": ["target_project_required"],
        "workdir": str(projected_workdir_state.get("workdir") or ""),
        "workdir_arg": workdir_arg,
        "workdir_state": dict(projected_workdir_state),
        "workdir_ready": False,
        "next_actions": [_fit_choose_workdir_action({}, cli_entry=normalized_cli_entry, language="en")],
        "route_actions_after_strong_fit": _localized_fit_next_actions(
            language="en",
            cli_entry=normalized_cli_entry,
            workdir_arg=workdir_arg,
            web_route=web_route,
            current_agent_host=current_agent_host,
        ),
        "direct_path_next_actions": _localized_direct_path_next_actions(language="en", include_record_action=False),
    }
    _project_fit_guidance_for_workdir(
        payload,
        task_review={},
        workdir_state=workdir_state,
        projected_workdir_state=projected_workdir_state,
        route_context={
            "workdir_arg": workdir_arg,
            "language": "en",
            "cli_entry": normalized_cli_entry,
            "web_route": web_route,
            "current_agent_host": current_agent_host,
        },
    )
    _project_fit_route_action_readiness(payload)
    _project_fit_route_readiness_summary(payload)
    _project_fit_review_action_readiness(payload)
    _project_fit_reviewed_setup_gate(payload)
    _project_fit_task_review_status(payload)
    _project_fit_summary_action_kinds(payload)
    _project_fit_direct_path_action_readiness(payload)
    _project_fit_command_field_boundary(payload)
    return payload
