from __future__ import annotations

from agent_adapter_test_support import cli_agent_adapter_commands


def test_cli_recoverable_context_prints_terminal_verdict_status(capsys) -> None:
    repair_choice = _repair_failed_preview_choice()

    cli_agent_adapter_commands._print_recoverable_context_choices({"confidence": "ambiguous", "choices": [_terminal_pass_choice(), repair_choice]})

    output = capsys.readouterr().out

    for term in (
        "- replay_terminal_pass: Replay terminal run: Ship the focused starter experience.",
        "choice_status: terminal_passed", "no new Agent work starts unless the task scope changes", "linked_run_status: succeeded",
        "task_verdict: passed", "task_verdict_summary: Required coverage has direct evidence.",
        "preview_path: /loops/new/bundle?alignment_session_id=align_failed", "validation_error: bundle metadata.name is required",
        "repair_focus:", "add metadata.name so the plan has a stable reviewable identity",
        "plan_file_to_repair: /tmp/bad-bundle.yml", "preview_plan_copy: /tmp/preview-bundle.yml", "selection_hint: one runnable context is available",
    ):
        assert term in output
    repair_summary = cli_agent_adapter_commands._recoverable_context_choice_summary(repair_choice)
    assert repair_summary["validation_error"] == "bundle metadata.name is required"
    assert repair_summary["repair_focus"] == ["add metadata.name so the plan has a stable reviewable identity"]


def test_cli_recoverable_context_list_keeps_runnable_choices_visible(capsys) -> None:
    non_runnable = [_unfinished_preview_choice(index) for index in range(5)]
    runnable = [_ready_preview_choice(), _terminal_pass_choice(updated_at="2026-05-19T20:09:10Z")]

    cli_agent_adapter_commands._print_recoverable_context_choices(
        {
            "confidence": "ambiguous",
            "choices": [*non_runnable, *runnable],
            "selection_hint": (
                "2 runnable contexts are available; choose the exact option_id for the active, READY, "
                "or terminal context you mean; non-runnable contexts need plan repair or Web review."
            ),
        }
    )

    output = capsys.readouterr().out

    for term in (
        "context_choices: 7 total / 2 runnable / 5 non-runnable",
        "- start_ready_preview: Start READY preview: Ship the focused starter experience.",
        "- replay_terminal_pass: Replay terminal run: Ship the focused starter experience.",
        "next_loop_command: /loopora-run option:agent_run:align_ready", "next_loop_command: /loopora-run option:agent_run:align_passed",
        "recoverable_contexts_omitted: 2 (0 runnable / 2 non-runnable)", "selection_hint: 2 runnable contexts are available",
    ):
        assert term in output
    assert "Unfinished preview 4" not in output


def test_cli_recoverable_context_prints_lifecycle_retry_choice(capsys) -> None:
    retry_choice = _lifecycle_retry_choice()

    cli_agent_adapter_commands._print_recoverable_context_choices({"confidence": "exact", "choices": [retry_choice]})

    output = capsys.readouterr().out

    for term in (
        "- retry_lifecycle_failure: Retry failed run start: Ship the focused starter experience.",
        "choice_status: terminal_retry",
        "failed before evidence work could start",
        "linked_run_status: failed",
        "linked_run_lifecycle_failure: true",
        "recording_blocked_reason: cannot accept lifecycle failure as a run result",
        "task_verdict: not_evaluated",
        "next_loop_command: /loopora-run option:agent_run:align_retry",
    ):
        assert term in output
    summary = cli_agent_adapter_commands._recoverable_context_choice_summary(retry_choice)
    assert summary["action"] == "retry_lifecycle_failure"
    assert summary["linked_run_lifecycle_failure"] is True
    assert summary["recording_blocked_reason"] == "cannot accept lifecycle failure as a run result"


def test_cli_terminal_passed_task_next_action_explains_no_next_pass(capsys) -> None:
    cli_agent_adapter_commands._print_terminal_task_next_action(
        {"status": "passed", "summary": "Required coverage has direct evidence."}
    )

    output = capsys.readouterr().out

    assert "task_next_action: task verdict already passed" in output
    assert "no new evidence pass will start unless the task scope changes" in output


def _terminal_pass_choice(*, updated_at: str = "2026-05-19T20:28:10Z") -> dict:
    return {
        "action": "replay_terminal_pass",
        "label_en": "Replay terminal run: Ship the focused starter experience.",
        "option_id": "agent_run:align_passed",
        "alignment_session_id": "align_passed",
        "linked_run_id": "run_passed",
        "linked_run_status": "succeeded",
        "choice_status": "terminal_passed",
        "choice_hint_en": (
            "Replay a terminal run whose task verdict already passed; no new Agent work starts unless the task scope changes."
        ),
        "task_verdict_status": "passed",
        "task_verdict_summary": "Required coverage has direct evidence.",
        "runnable": True,
        "alignment_status": "running_loop",
        "updated_at": updated_at,
        "next_slash_command": "/loopora-run option:agent_run:align_passed",
        "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_passed",
    }


def _lifecycle_retry_choice() -> dict:
    return {
        "action": "retry_lifecycle_failure",
        "label_en": "Retry failed run start: Ship the focused starter experience.",
        "option_id": "agent_run:align_retry",
        "alignment_session_id": "align_retry",
        "linked_run_id": "run_failed_start",
        "linked_run_status": "failed",
        "linked_run_lifecycle_failure": True,
        "recording_blocked_reason": "cannot accept lifecycle failure as a run result",
        "choice_status": "terminal_retry",
        "choice_hint_en": (
            "Retry a terminal run that failed before evidence work could start; selecting this starts a fresh run from the reviewed Loop."
        ),
        "task_verdict_status": "not_evaluated",
        "task_verdict_summary": "No evidence ledger entries are available yet.",
        "runnable": True,
        "alignment_status": "running_loop",
        "updated_at": "2026-05-19T20:28:10Z",
        "next_slash_command": "/loopora-run option:agent_run:align_retry",
        "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_retry",
    }


def _repair_failed_preview_choice() -> dict:
    return {
        "action": "repair_failed_preview",
        "label_en": "Repair Agent plan: older failed preview",
        "option_id": "agent_run:align_failed",
        "alignment_session_id": "align_failed",
        "choice_status": "needs_repair",
        "choice_hint_en": "Candidate plan failed validation; repair it with /loopora-plan before selecting it.",
        "runnable": False,
        "preview_path": "/loops/new/bundle?alignment_session_id=align_failed",
        "validation_error": "bundle metadata.name is required",
        "plan_file_to_repair": "/tmp/bad-bundle.yml",
        "preview_plan_copy": "/tmp/preview-bundle.yml",
        "next_repair_step": (
            "repair the candidate plan file so it preserves repair_task_message and repair_focus in spec, "
            "roles, workflow, and evidence rules; rerun repair_cli_command or repair_slash_command, then "
            "use /loopora-run only after the preview is ready"
        ),
        "next_plan_command": "/loopora-plan",
    }


def _ready_preview_choice() -> dict:
    return {
        "action": "start_ready_preview",
        "label_en": "Start READY preview: Ship the focused starter experience.",
        "option_id": "agent_run:align_ready",
        "alignment_session_id": "align_ready",
        "choice_status": "ready_preview",
        "choice_hint_en": "Start this READY preview as a run; choose this if it is the plan you just reviewed.",
        "runnable": True,
        "alignment_status": "ready",
        "updated_at": "2026-05-19T20:10:10Z",
        "next_slash_command": "/loopora-run option:agent_run:align_ready",
        "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_ready",
    }


def _unfinished_preview_choice(index: int) -> dict:
    return {
        "action": "preview_not_ready",
        "label_en": f"Unfinished preview {index}",
        "option_id": f"agent_run:align_unfinished_{index}",
        "alignment_session_id": f"align_unfinished_{index}",
        "choice_status": "not_ready",
        "choice_hint_en": "Not runnable yet; return to /loopora-plan or Web review before selecting it.",
        "runnable": False,
        "alignment_status": "idle",
        "updated_at": f"2026-05-19T20:2{index}:10Z",
        "next_plan_command": "/loopora-plan",
    }
