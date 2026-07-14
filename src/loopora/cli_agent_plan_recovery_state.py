from __future__ import annotations

from loopora.agent_entry_candidate import (
    READY_CANDIDATE_NEXT_STEP,
    READY_REVIEW_BEFORE_LOOP,
    agent_ready_task_anchor_projection,
)
from loopora.cli_agent_plan_recovery_assets import (
    ALIGNMENT_QUESTION_NEXT_MESSAGE_POLICY,
    ALIGNMENT_QUESTION_NEXT_STEP,
    ALIGNMENT_QUESTION_SUBAGENT_POLICY,
)
from loopora.cli_agent_plan_recovery_common import (
    _agent_entry_return_run_command,
    _agent_entry_return_slash_command,
    _latest_alignment_question,
)
from loopora.cli_agent_plan_recovery_repair import (
    _attach_agent_candidate_repair_fields,
    _attach_agent_context_card_repair_fields,
)
from loopora.cli_agent_plan_recovery_web_review import _attach_agent_web_review_recovery_fields


def _attach_agent_gen_recovery_fields(result: dict) -> None:
    if result.get("ready"):
        return
    if str(result.get("status") or "").strip() == "skipped":
        result["loop_recovery"] = "alignment_skipped"
        result["requires_web_alignment"] = False
        return
    if result.get("requires_context_repair"):
        _attach_agent_context_card_repair_fields(result)
        return
    if result.get("requires_candidate_repair"):
        _attach_agent_candidate_repair_fields(result)
        return
    if result.get("continued_alignment_session") and result.get("requires_web_alignment"):
        result["loop_recovery"] = "continue_alignment_dialogue"
        result["ask_user"] = _latest_alignment_question(result)
        result["question_action"] = {
            "target": "main_agent_session",
            "must_wait_for_user_reply": True,
            "subagent_policy": ALIGNMENT_QUESTION_SUBAGENT_POLICY,
            "next_message_policy": ALIGNMENT_QUESTION_NEXT_MESSAGE_POLICY,
        }
        result["next_alignment_step"] = ALIGNMENT_QUESTION_NEXT_STEP
        return
    if result.get("requires_web_alignment"):
        _attach_agent_web_review_recovery_fields(result)


def _attach_agent_ready_run_handoff_fields(result: dict) -> None:
    if not result.get("ready"):
        return
    for key, value in agent_ready_task_anchor_projection(result.get("session") or {}).items():
        result.setdefault(key, value)
    result["review_before_loop"] = READY_REVIEW_BEFORE_LOOP
    result["ready_next_step"] = READY_CANDIDATE_NEXT_STEP
    result["ready_slash_command"] = _agent_entry_return_slash_command()
    command = _agent_entry_return_run_command(result)
    if command:
        result["ready_cli_command"] = command
        result["ready_run_command"] = command
