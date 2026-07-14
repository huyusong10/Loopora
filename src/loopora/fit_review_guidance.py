from __future__ import annotations

from collections.abc import Mapping

from loopora.agent_adapter_command_prefix import DEFAULT_LOOPORA_CLI_ENTRY
from loopora.fit_review_completion_commands import (
    _fit_direct_decision_completion_command as _fit_direct_decision_completion_command,
    _fit_review_completion_action as _fit_review_completion_action,
    _fit_review_completion_command as _fit_review_completion_command,
    _fit_supplied_review_option_args as _fit_supplied_review_option_args,
)
from loopora.fit_review_catalog import (
    FIRST_TASK_REVIEW_INPUT_IDS,
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
    _completion_placeholders,
)
from loopora.fit_review_first_task_messages import (
    _fit_first_task_message_example as _fit_first_task_message_example,
    _fit_first_task_message_example_state as _fit_first_task_message_example_state,
    _fit_review_draft_first_task_message as _fit_review_draft_first_task_message,
    _primary_first_task_message as _primary_first_task_message,
    _primary_first_task_message_state as _primary_first_task_message_state,
    _primary_first_task_message_state_payload as _primary_first_task_message_state_payload,
    _project_primary_first_task_message_state as _project_primary_first_task_message_state,
)

__all__ = [
    "FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS",
    "FIT_DIRECT_DECISION_COMPLETION_PLACEHOLDERS_ZH",
    "FIT_FIRST_TASK_MESSAGE_STATUS",
    "FIT_REVIEW_COMPLETION_PLACEHOLDERS",
    "FIT_REVIEW_COMPLETION_PLACEHOLDERS_ZH",
    "FIT_REVIEW_INPUT_FIELDS",
    "FIT_REVIEW_SETUP_GATE",
    "PREFER_DIRECT_AGENT_OR_CHECK_ITEMS",
    "STRONG_FIT_SIGNAL_ITEMS",
    "TASK_FIT_REVIEW_QUESTIONS",
]


def _normalize_task_text(task_text: str) -> str:
    return " ".join(task_text.split())


def _task_fit_setup_gate(*, ready: bool, prefer_direct: bool = False) -> dict[str, object]:
    if prefer_direct:
        return {
            "setup_allowed": False,
            "setup_gate": FIT_REVIEW_SETUP_GATE["direct"],
            "setup_blocker": FIT_REVIEW_SETUP_GATE["direct_blocker"],
        }
    return {
        "setup_allowed": ready,
        "setup_gate": FIT_REVIEW_SETUP_GATE["ready"] if ready else FIT_REVIEW_SETUP_GATE["blocked"],
        "setup_blocker": "none" if ready else FIT_REVIEW_SETUP_GATE["blocker"],
    }


def _direct_decision_input_supplied(*, direct_path_check: str) -> bool:
    return bool(direct_path_check)


def _task_fit_review_payload(  # noqa: PLR0913 - mirrors public fit review inputs plus current CLI entry.
    task_text: str,
    *,
    loopora_fit_reason: str = "",
    fake_done_risks: str = "",
    required_evidence: str = "",
    judgment_tradeoffs: str = "",
    direct_path_check: str = "",
    prefer_direct: bool = False,
    language: str = "en",
    cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY,
    completion_workdir: str = "",
) -> dict[str, object]:
    normalized_task = _normalize_task_text(task_text)
    normalized_fit_reason = _normalize_task_text(loopora_fit_reason)
    normalized_fake_done = _normalize_task_text(fake_done_risks)
    normalized_evidence = _normalize_task_text(required_evidence)
    normalized_tradeoffs = _normalize_task_text(judgment_tradeoffs)
    normalized_direct_path = _normalize_task_text(direct_path_check)
    direct_decision_has_input = _direct_decision_input_supplied(
        direct_path_check=normalized_direct_path,
    )
    prefer_direct_ready = prefer_direct and direct_decision_has_input
    prefer_direct_needs_input = prefer_direct and not direct_decision_has_input
    if not any(
        (
            normalized_task,
            normalized_fit_reason,
            normalized_fake_done,
            normalized_evidence,
            normalized_tradeoffs,
            normalized_direct_path,
            prefer_direct,
        )
    ):
        return {}
    placeholders = _completion_placeholders(language=language)
    task_slot = normalized_task or placeholders["task"]
    fit_reason_slot = normalized_fit_reason or placeholders["loopora_fit_reason"]
    fake_done_slot = normalized_fake_done or placeholders["fake_done_risks"]
    evidence_slot = normalized_evidence or placeholders["required_evidence"]
    tradeoff_slot = normalized_tradeoffs or placeholders["judgment_tradeoffs"]
    direct_path_slot = normalized_direct_path
    review_inputs = {
        "task": normalized_task,
        "loopora_fit_reason": normalized_fit_reason,
        "fake_done_risks": normalized_fake_done,
        "required_evidence": normalized_evidence,
        "judgment_tradeoffs": normalized_tradeoffs,
        "direct_path_check": normalized_direct_path,
    }
    if prefer_direct_ready:
        missing_input_ids = []
    elif prefer_direct_needs_input:
        missing_input_ids = ["direct_decision_input"]
    else:
        missing_input_ids = [input_id for input_id in FIRST_TASK_REVIEW_INPUT_IDS if not review_inputs[input_id]]
    ready_for_loopora_plan_message = not missing_input_ids and not prefer_direct
    draft_status = (
        FIT_FIRST_TASK_MESSAGE_STATUS["direct"]
        if prefer_direct_ready
        else FIT_FIRST_TASK_MESSAGE_STATUS["direct_input"]
        if prefer_direct_needs_input
        else FIT_FIRST_TASK_MESSAGE_STATUS["ready"]
        if ready_for_loopora_plan_message
        else FIT_FIRST_TASK_MESSAGE_STATUS["preview"]
    )
    review_completion_command = (
        ""
        if ready_for_loopora_plan_message or prefer_direct_ready
        else _fit_direct_decision_completion_command(
            review_inputs,
            language=language,
            cli_entry=cli_entry,
            workdir=completion_workdir,
        )
        if prefer_direct_needs_input
        else _fit_review_completion_command(
            review_inputs,
            language=language,
            cli_entry=cli_entry,
            workdir=completion_workdir,
        )
    )
    setup_gate = (
        {
            "setup_allowed": False,
            "setup_gate": FIT_REVIEW_SETUP_GATE["blocked"],
            "setup_blocker": FIT_REVIEW_SETUP_GATE["direct_input_blocker"],
        }
        if prefer_direct_needs_input
        else _task_fit_setup_gate(ready=ready_for_loopora_plan_message, prefer_direct=prefer_direct_ready)
    )
    return {
        "task_fit_review_summary": {
            "task_supplied": bool(normalized_task),
            "review_input_supplied": True,
            "human_judgment_required": True,
            "not_a_classifier": True,
            "review_path": "answer_fit_questions_before_setup",
            "complete_first_task_message": ready_for_loopora_plan_message,
            "ready_for_loopora_plan_message": ready_for_loopora_plan_message,
            "draft_first_task_message_copy_allowed": ready_for_loopora_plan_message,
            "draft_first_task_message_status": draft_status,
            "missing_input_count": len(missing_input_ids),
            "review_completion_command_available": bool(review_completion_command),
            "prefer_direct_path": prefer_direct,
            "direct_decision_input_supplied": direct_decision_has_input,
            "fit_decision": "prefer_direct_path"
            if prefer_direct_ready
            else "needs_direct_decision_input"
            if prefer_direct_needs_input
            else ("strong_fit_review_complete" if ready_for_loopora_plan_message else "needs_review_inputs"),
            **setup_gate,
        },
        "review_inputs": review_inputs,
        "required_first_task_input_ids": list(FIRST_TASK_REVIEW_INPUT_IDS),
        "missing_first_task_input_ids": missing_input_ids,
        "next_review_action": (
            "use_direct_agent_or_hard_checks"
            if prefer_direct_ready
            else "fill_direct_decision_before_setup"
            if prefer_direct_needs_input
            else "copy_draft_after_review"
            if ready_for_loopora_plan_message
            else "fill_missing_judgment_before_setup"
        ),
        "review_completion_command": review_completion_command,
        "task": normalized_task,
        "strong_fit_signal_ids": [item["id"] for item in STRONG_FIT_SIGNAL_ITEMS],
        "direct_path_signal_ids": [item["id"] for item in PREFER_DIRECT_AGENT_OR_CHECK_ITEMS],
        "review_questions": [dict(item) for item in TASK_FIT_REVIEW_QUESTIONS],
        "draft_first_task_message": ""
        if prefer_direct
        else _fit_review_draft_first_task_message(
            slots={
                "task": task_slot,
                "loopora_fit_reason": fit_reason_slot,
                "fake_done_risks": fake_done_slot,
                "required_evidence": evidence_slot,
                "judgment_tradeoffs": tradeoff_slot,
                "direct_path_check": direct_path_slot,
            },
            language=language,
        ),
    }


def _task_fit_review_ready_for_setup(task_review: dict[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary")
    return isinstance(summary, dict) and bool(summary.get("setup_allowed"))


def _task_fit_review_ready_for_plan_message(task_review: Mapping[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    return isinstance(summary, Mapping) and bool(summary.get("ready_for_loopora_plan_message"))


def _task_fit_review_prefers_direct(task_review: Mapping[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    return isinstance(summary, Mapping) and str(summary.get("setup_blocker") or "") == FIT_REVIEW_SETUP_GATE["direct_blocker"]


def _task_fit_review_needs_direct_decision_input(task_review: Mapping[str, object]) -> bool:
    summary = task_review.get("task_fit_review_summary") if isinstance(task_review, Mapping) else {}
    return isinstance(summary, Mapping) and str(summary.get("setup_blocker") or "") == FIT_REVIEW_SETUP_GATE["direct_input_blocker"]
