from __future__ import annotations

from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_status as _agent_v3_status
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_plan_recovery_results import (
    _agent_gen_error_summary as _agent_gen_error_summary,
    _attach_agent_ready_run_handoff_fields as _attach_agent_ready_run_handoff_fields,
)
from loopora.cli_summary_helpers import (
    set_summary_list as _set_summary_list,
    set_summary_mapping as _set_summary_mapping,
    set_summary_text as _set_summary_text,
)


def _agent_gen_json_payload(result: dict, *, include_raw: bool = True) -> dict:
    summary = _agent_plan_summary(result, compact=not include_raw)
    extras: dict[str, object] = {
        "technical_handoff": _agent_v3_technical_handoff(summary),
        "diagnostics": {"legacy_summary_key": "agent_plan_summary"},
    }
    if include_raw:
        extras["raw"] = _agent_v3_legacy_raw(summary_key="agent_plan_summary", summary=summary, payload=result)
    return _agent_v3_envelope(
        kind="agent_plan",
        status=_agent_v3_status(ready=result.get("ready"), error=result.get("validation_error") or result.get("error")),
        summary=summary,
        extras=extras,
    )


def _agent_plan_summary(result: dict, *, compact: bool = False) -> dict:
    _attach_agent_ready_run_handoff_fields(result)
    status = str(result.get("status") or "").strip()
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "status": status,
        "loop_recovery": str(result.get("loop_recovery") or "").strip(),
        "requires_web_alignment": bool(result.get("requires_web_alignment")),
        "requires_candidate_repair": bool(result.get("requires_candidate_repair")),
        "requires_context_repair": bool(result.get("requires_context_repair")),
        "loopora_fit_contradiction": bool(result.get("loopora_fit_contradiction")),
    }
    _attach_plan_repair_summary_fields(summary, result)
    _set_summary_text(summary, "context_binding_error", result.get("context_binding_error"))
    _set_summary_text(summary, "workdir", result.get("workdir"))
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_list(summary, "required_inputs", result.get("required_inputs"))
    _set_summary_text(summary, "ask_user", result.get("ask_user"))
    _set_summary_mapping(summary, "question_action", result.get("question_action"))
    _set_summary_text(summary, "example_user_reply", result.get("example_user_reply"))
    _set_summary_text(summary, "message_source_policy", result.get("message_source_policy"))
    _set_summary_text(summary, "message_cli_command", result.get("message_cli_command"))
    _set_summary_text(summary, "next_plan_cli_command", result.get("next_plan_cli_command"))
    _set_summary_text(summary, "next_plan_cli_command_policy", result.get("next_plan_cli_command_policy"))
    _set_summary_text(summary, "task_message_template", result.get("task_message_template"))
    _set_summary_text(summary, "first_task_message_example", result.get("first_task_message_example"))
    for key in ("first_task_message_example_state", "first_task_handoff_policy"):
        _set_summary_mapping(summary, key, result.get(key))
    _set_summary_text(summary, "debug_cli_example_command", result.get("debug_cli_example_command"))
    _set_summary_text(summary, "next", result.get("next"))
    _attach_alignment_session_summary_fields(summary, result)
    _attach_alignment_dialogue_summary_fields(summary, result)
    if status != "skipped":
        _set_summary_text(summary, "preview_url", result.get("preview_url") or result.get("preview_path"))
        _set_summary_text(summary, "preview_url_status", result.get("preview_url_status"))
        _set_summary_text(summary, "preview_url_web_start_command", result.get("preview_url_web_start_command"))
    attach_native_run_surface(summary, result, compact=compact)
    _set_summary_text(summary, "next_review_step", result.get("next_review_step"))
    _set_summary_text(summary, "review_status", result.get("review_status"))
    _set_summary_list(summary, "review_focus", result.get("review_focus"))
    _attach_task_review_summary_fields(summary, result)
    _set_summary_text(summary, "review_recommended_action", result.get("review_recommended_action"))
    _set_summary_text(summary, "review_reply_message", result.get("review_reply_message"))
    _set_summary_text(summary, "review_reply_preview", result.get("review_reply_preview"))
    _set_summary_text(summary, "after_review_ready", result.get("after_review_ready"))
    _set_summary_text(summary, "run_blocked_until_web_review", result.get("run_blocked_until_web_review"))
    _set_summary_text(summary, "after_review_cli_command_status", result.get("after_review_cli_command_status"))
    _set_summary_text(summary, "after_review_slash_command", result.get("after_review_slash_command"))
    _set_summary_text(summary, "after_web_review_cli_command", result.get("after_web_review_cli_command"))
    _set_summary_text(summary, "after_review_cli_command", result.get("after_review_cli_command"))
    _set_summary_text(summary, "after_review_command", result.get("after_review_command"))
    if result.get("ready"):
        _set_summary_mapping(summary, "ready_review_projection", result.get("ready_review_projection"))
        _set_summary_text(summary, "review_before_loop", result.get("review_before_loop"))
        _set_summary_text(summary, "ready_next_step", result.get("ready_next_step"))
        _set_summary_text(summary, "ready_slash_command", result.get("ready_slash_command"))
        _set_summary_text(summary, "ready_cli_command", result.get("ready_cli_command"))
        _set_summary_text(summary, "ready_run_command", result.get("ready_run_command"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_alignment_session_summary_fields(summary: dict[str, object], result: dict) -> None:
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    _set_summary_text(summary, "alignment_session_id", session.get("id"))
    _set_summary_text(summary, "alignment_stage", session.get("alignment_stage"))


def _attach_alignment_dialogue_summary_fields(summary: dict[str, object], result: dict) -> None:
    if result.get("continued_alignment_session") is not True:
        return
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    summary["continued_alignment_session"] = True
    latest = _latest_alignment_assistant_turn(session)
    _set_summary_text(summary, "alignment_assistant_message", latest.get("content"))
    options = latest.get("decision_options")
    if isinstance(options, list) and options:
        summary["alignment_decision_options"] = options
    missing_items = latest.get("missing_items")
    if isinstance(missing_items, list) and missing_items:
        summary["alignment_missing_items"] = [str(item).strip() for item in missing_items if str(item).strip()]
    _set_summary_text(summary, "next_alignment_step", result.get("next_alignment_step"))


def _latest_alignment_assistant_turn(session: dict) -> dict:
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    for item in reversed(transcript):
        if isinstance(item, dict) and str(item.get("role") or "").strip() == "assistant":
            return item
    return {}


def _attach_plan_repair_summary_fields(summary: dict[str, object], result: dict) -> None:
    _set_summary_mapping(summary, "agent_work_panel", result.get("agent_work_panel"))
    _set_summary_mapping(summary, "repair_action", result.get("repair_action"))
    _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
    _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
    _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
    _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
    _set_summary_text(summary, "repair_slash_command", result.get("repair_slash_command"))
    _set_summary_text(summary, "repair_cli_command", result.get("repair_cli_command"))
    _set_summary_text(summary, "repair_cli_command_policy", result.get("repair_cli_command_policy"))
    _set_summary_text(summary, "repair_reference", result.get("repair_reference"))
    _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))


def _attach_task_review_summary_fields(summary: dict[str, object], result: dict) -> None:
    for key in ("ready_meaning", "task_anchor_status", "task_anchor", "task_anchor_preview", "review_scope"):
        _set_summary_text(summary, key, result.get(key))
