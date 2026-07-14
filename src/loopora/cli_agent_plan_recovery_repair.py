from __future__ import annotations

import shlex

from loopora.cli_agent_plan_recovery_assets import (
    CONTEXT_CARD_REPAIR_NEXT_ACTION,
    REPAIR_CLI_COMMAND_POLICY,
    REPAIR_FORBIDDEN_ACTIONS,
    REPAIR_NEXT_ACTION,
    REPAIR_NEXT_REPAIR_STEP,
    REPAIR_REFERENCE,
)
from loopora.cli_agent_plan_recovery_common import (
    _agent_gen_error_summary,
    _agent_repair_cli_command,
    _agent_task_message_from_session,
)
from loopora.cli_agent_plan_repair_hints import validation_repair_hints as _validation_repair_hints


def _attach_agent_context_card_repair_fields(result: dict) -> None:
    result["loop_recovery"] = "repair_agent_context_card"
    error = _agent_gen_error_summary(result)
    result["validation_error"] = error
    result["repair_focus"] = _validation_repair_hints(error)
    result["next_plan_command"] = "/loopora-plan"
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    plan_file = str(binding.get("source_path") or "").strip()
    result["preview_plan_copy"] = str(session.get("bundle_path") or "").strip()
    repair_cli_command = _agent_repair_cli_command(result, plan_file=plan_file)
    if repair_cli_command:
        result["repair_cli_command"] = repair_cli_command
        result["repair_cli_command_policy"] = REPAIR_CLI_COMMAND_POLICY
    action = _agent_context_card_repair_action(result)
    result["agent_work_panel"] = {
        "state": "repair_agent_context_card",
        "task_proven": False,
        "task_outcome": "not_ready_repair_agent_context_card",
        "next_action": action["next_action"],
        "evidence_focus": "validation_error and repair_focus for the Agent context-card save failure",
        "todo_items": [
            "fix target project .loopora agent-state write access",
            "rerun /loopora-plan in the same Agent session",
            "start /loopora-run only after the context card is saved",
        ],
    }
    result["repair_action"] = action


def _attach_agent_candidate_repair_fields(result: dict) -> None:
    result["loop_recovery"] = "repair_candidate_plan_file"
    error = _agent_gen_error_summary(result)
    result["validation_error"] = error
    result["repair_focus"] = _validation_repair_hints(error)
    repair_task_message = _agent_task_message_from_session(result)
    if repair_task_message:
        result["repair_task_message"] = repair_task_message
    session = result.get("session") if isinstance(result.get("session"), dict) else {}
    binding = result.get("binding") if isinstance(result.get("binding"), dict) else {}
    plan_file = str(binding.get("source_path") or session.get("bundle_path") or "").strip()
    result["plan_file_to_repair"] = plan_file
    result["preview_plan_copy"] = str(session.get("bundle_path") or "").strip()
    result["next_plan_command"] = "/loopora-plan"
    if plan_file:
        result["repair_slash_command"] = f"/loopora-plan {shlex.quote(plan_file)}"
    repair_cli_command = _agent_repair_cli_command(result, plan_file=plan_file)
    if repair_cli_command:
        result["repair_cli_command"] = repair_cli_command
        result["repair_cli_command_policy"] = REPAIR_CLI_COMMAND_POLICY
    result["repair_reference"] = REPAIR_REFERENCE
    result["next_repair_step"] = REPAIR_NEXT_REPAIR_STEP
    action = _agent_plan_repair_action(result)
    if action:
        result["agent_work_panel"] = {
            "state": "repair_candidate_plan_file",
            "task_proven": False,
            "task_outcome": "not_ready_repair_candidate_plan_file",
            "next_action": action["next_action"],
            "evidence_focus": "validation_error and repair_focus from the rejected candidate plan",
            "todo_items": [
                "edit the candidate plan file",
                "rerun repair_cli_command exactly with compact JSON",
                "start /loopora-run only after preview readiness",
            ],
        }
        result["repair_action"] = action


def _agent_plan_repair_action(result: dict) -> dict[str, object]:
    plan_file = str(result.get("plan_file_to_repair") or "").strip()
    next_command = str(result.get("repair_cli_command") or result.get("repair_slash_command") or "").strip()
    action: dict[str, object] = {
        "state": "repair_candidate_plan_file",
        "next_action": REPAIR_NEXT_ACTION,
        "allowed_inputs": [
            "validation_error",
            "repair_focus",
            "repair_task_message",
            "target project .loopora state",
            "managed Candidate Bundle Skeleton",
            "the candidate plan file itself",
        ],
        "forbidden_actions": list(REPAIR_FORBIDDEN_ACTIONS),
        "stop_before": "/loopora-run until the repaired preview returns ready=true",
    }
    if plan_file:
        action["file_to_edit"] = plan_file
    if next_command:
        action["command_after_edit"] = next_command
    return action


def _agent_context_card_repair_action(result: dict) -> dict[str, object]:
    next_command = str(result.get("repair_cli_command") or "").strip()
    action: dict[str, object] = {
        "state": "repair_agent_context_card",
        "next_action": CONTEXT_CARD_REPAIR_NEXT_ACTION,
        "allowed_inputs": [
            "validation_error",
            "repair_focus",
            "target project .loopora agent state",
            "preview_url",
            "preview_plan_copy",
        ],
        "forbidden_actions": list(REPAIR_FORBIDDEN_ACTIONS),
        "stop_before": "/loopora-run until the context card save succeeds or the user chooses a recoverable context",
    }
    if next_command:
        action["command_after_repair"] = next_command
    return action
