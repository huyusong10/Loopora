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


def _agent_gen_json_payload(result: dict) -> dict:
    summary = _agent_plan_summary(result)
    return _agent_v3_envelope(
        kind="agent_plan",
        status=_agent_v3_status(ready=result.get("ready"), error=result.get("validation_error") or result.get("error")),
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_plan_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_plan_summary", summary=summary, payload=result),
        },
    )


def _agent_plan_summary(result: dict) -> dict:
    _attach_agent_ready_run_handoff_fields(result)
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "status": str(result.get("status") or "").strip(),
        "loop_recovery": str(result.get("loop_recovery") or "").strip(),
        "requires_web_alignment": bool(result.get("requires_web_alignment")),
        "requires_candidate_repair": bool(result.get("requires_candidate_repair")),
        "loopora_fit_contradiction": bool(result.get("loopora_fit_contradiction")),
    }
    attach_native_run_surface(summary, result)
    _set_summary_text(summary, "workdir", result.get("workdir"))
    _set_summary_text(summary, "message", result.get("message"))
    _set_summary_list(summary, "required_inputs", result.get("required_inputs"))
    _set_summary_text(summary, "ask_user", result.get("ask_user"))
    _set_summary_mapping(summary, "question_action", result.get("question_action"))
    _set_summary_text(summary, "example_user_reply", result.get("example_user_reply"))
    _set_summary_text(summary, "task_message_template", result.get("task_message_template"))
    _set_summary_text(summary, "first_task_message_example", result.get("first_task_message_example"))
    _set_summary_text(summary, "debug_cli_example_command", result.get("debug_cli_example_command"))
    _set_summary_text(summary, "next", result.get("next"))
    _set_summary_text(summary, "preview_url", result.get("preview_url") or result.get("preview_path"))
    _set_summary_text(summary, "validation_error", result.get("validation_error") or _agent_gen_error_summary(result))
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_text(summary, "repair_task_message", result.get("repair_task_message"))
    _set_summary_text(summary, "plan_file_to_repair", result.get("plan_file_to_repair"))
    _set_summary_text(summary, "preview_plan_copy", result.get("preview_plan_copy"))
    _set_summary_text(summary, "next_plan_command", result.get("next_plan_command"))
    _set_summary_text(summary, "repair_slash_command", result.get("repair_slash_command"))
    _set_summary_text(summary, "repair_cli_command", result.get("repair_cli_command"))
    _set_summary_text(summary, "next_repair_step", result.get("next_repair_step"))
    _set_summary_text(summary, "next_review_step", result.get("next_review_step"))
    _set_summary_text(summary, "review_status", result.get("review_status"))
    _set_summary_list(summary, "review_focus", result.get("review_focus"))
    _set_summary_text(summary, "task_anchor_status", result.get("task_anchor_status"))
    _set_summary_text(summary, "task_anchor_preview", result.get("task_anchor_preview"))
    _set_summary_text(summary, "review_scope", result.get("review_scope"))
    _set_summary_text(summary, "review_recommended_action", result.get("review_recommended_action"))
    _set_summary_text(summary, "review_reply_preview", result.get("review_reply_preview"))
    _set_summary_text(summary, "after_review_ready", result.get("after_review_ready"))
    _set_summary_text(summary, "after_review_slash_command", result.get("after_review_slash_command"))
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
