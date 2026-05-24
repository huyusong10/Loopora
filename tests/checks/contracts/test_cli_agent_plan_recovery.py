from __future__ import annotations

from loopora.cli_agent_plan_recovery import (
    agent_plan_error_requires_message,
    agent_plan_message_required_result,
    print_agent_plan_message_required,
)


def test_agent_plan_message_required_recovery_keeps_single_question_and_native_surface(tmp_path, capsys) -> None:
    result = agent_plan_message_required_result(
        adapter="codex",
        workdir=tmp_path,
        context_id="ctx_123",
        entry_source="codex_project_skill",
    )

    assert agent_plan_error_requires_message("missing --message task summary") is True
    assert agent_plan_error_requires_message("different validation error") is False
    assert result["loop_recovery"] == "plan_message_required"
    assert result["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert result["question_action"]["target"] == "main_agent_session"
    assert result["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert result["task_message_template"].startswith("Goal:")
    assert "loopora agent codex plan" in result["debug_cli_example_command"]
    assert "--context-id ctx_123" in result["debug_cli_example_command"]
    assert "--entry-source codex_project_skill" in result["debug_cli_example_command"]

    print_agent_plan_message_required(result)
    output = capsys.readouterr().out

    assert output.count("required_inputs:") == 1
    assert "ask_user: What long-running task should Loopora govern?" in output
    assert "question_action: Use the host's official user-question or follow-up capability" in output
    assert "first_task_message_example:" in output
    assert "debug_cli_example_command:" in output
    assert "native surface:" in output
    assert "- host dispatch: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output
