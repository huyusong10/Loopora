from __future__ import annotations

from loopora.service_alignment_run_context_choices import (
    AgentRunContextNextActionRequest,
    agent_run_context_choice_payload,
    agent_run_context_choice_summary,
    agent_run_context_next_action,
)


EXPECTED_CHOICE_COUNT = 3
EXPECTED_NON_RUNNABLE_CHOICE_COUNT = 1
EXPECTED_RUNNABLE_CHOICE_COUNT = 2


def test_agent_run_context_next_action_maps_terminal_verdicts_and_stale_links() -> None:
    assert (
        agent_run_context_next_action(
            AgentRunContextNextActionRequest(
                session_status="ready",
                linked_run_id="run_passed",
                linked_run_status="succeeded",
                task_verdict_status="passed",
            )
        )
        == "replay_terminal_pass"
    )
    assert (
        agent_run_context_next_action(
            AgentRunContextNextActionRequest(
                session_status="ready",
                linked_run_id="run_unproven",
                linked_run_status="succeeded",
                task_verdict_status="continue_required",
            )
        )
        == "continue_terminal_evidence"
    )
    assert (
        agent_run_context_next_action(
            AgentRunContextNextActionRequest(
                session_status="ready",
                linked_run_id="run_lifecycle_failure",
                linked_run_status="failed",
                task_verdict_status="not_evaluated",
                linked_run_lifecycle_failure=True,
            )
        )
        == "retry_lifecycle_failure"
    )
    assert (
        agent_run_context_next_action(
            AgentRunContextNextActionRequest(
                session_status="ready",
                linked_run_id="run_missing",
                linked_run_found=False,
            )
        )
        == "stale_linked_run"
    )


def test_agent_run_context_choice_payload_separates_runnable_and_repair_commands(tmp_path) -> None:
    session = {
        "id": "align_ready",
        "status": "ready",
        "workdir": str(tmp_path),
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    runnable = agent_run_context_choice_payload(
        session,
        adapter="codex",
        payload={"entry_source": "codex_project_skill", "host_context_id": "thread-a"},
        title="Ready preview",
        next_action="start_ready_preview",
    )
    repair = agent_run_context_choice_payload(
        {**session, "status": "failed"},
        adapter="codex",
        title="Failed preview",
        next_action="repair_failed_preview",
    )

    assert runnable["runnable"] is True
    assert runnable["choice_status"] == "ready_preview"
    assert runnable["next_command"] == "/loopora-run option:agent_run:align_ready"
    assert "--source-option-id agent_run:align_ready" in runnable["next_cli_command"]
    assert runnable["entry_source"] == "codex_project_skill"
    assert runnable["host_context_id"] == "thread-a"
    assert repair["runnable"] is False
    assert repair["next_plan_command"] == "/loopora-plan"
    assert repair["next_command"] == ""
    assert repair["next_cli_command"] == ""


def test_agent_run_context_choice_payload_does_not_synthesize_cli_workdir_from_blank_session() -> None:
    choice = agent_run_context_choice_payload(
        {"id": "align_blank", "status": "ready", "workdir": ""},
        adapter="codex",
        title="Ready preview with damaged workdir",
        next_action="start_ready_preview",
    )

    assert choice["runnable"] is True
    assert choice["next_command"] == "/loopora-run option:agent_run:align_blank"
    assert choice["next_cli_command"] == ""


def test_agent_run_context_choice_payload_names_lifecycle_failure_retry(tmp_path) -> None:
    session = {
        "id": "align_retry",
        "status": "running_loop",
        "workdir": str(tmp_path),
        "linked_run_id": "run_failed_start",
    }

    retry = agent_run_context_choice_payload(
        session,
        adapter="codex",
        title="Retry failed start",
        linked_run_status="failed",
        task_verdict_status="not_evaluated",
        task_verdict_summary="No evidence ledger entries are available yet.",
        linked_run_lifecycle_failure=True,
        recording_blocked_reason="cannot accept lifecycle failure as a run result",
        next_action="retry_lifecycle_failure",
    )

    assert retry["runnable"] is True
    assert retry["action"] == "retry_lifecycle_failure"
    assert retry["choice_status"] == "terminal_retry"
    assert retry["linked_run_lifecycle_failure"] is True
    assert retry["recording_blocked_reason"] == "cannot accept lifecycle failure as a run result"
    assert retry["next_command"] == "/loopora-run option:agent_run:align_retry"
    assert retry["label_en"].startswith("Retry failed run start:")
    assert "fresh run" in retry["choice_hint_en"]


def test_agent_run_context_choice_summary_counts_only_dict_choices() -> None:
    summary = agent_run_context_choice_summary(
        [
            {"runnable": True},
            {"runnable": False},
            "not-a-choice",
            {},
        ]
    )

    assert summary["choice_count"] == EXPECTED_CHOICE_COUNT
    assert summary["runnable_choice_count"] == EXPECTED_RUNNABLE_CHOICE_COUNT
    assert summary["non_runnable_choice_count"] == EXPECTED_NON_RUNNABLE_CHOICE_COUNT
    assert "runnable contexts" in summary["selection_hint"]
