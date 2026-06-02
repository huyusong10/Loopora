from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_loopora_agent_command,
    _error_text,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_loop_json_without_plan_returns_structured_plan_first_recovery(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "plan_first"
    assert summary["next_plan_command"] == "/loopora-plan"
    assert summary["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["kind"] == "ask_user"
    assert summary["question_action"]["target"] == "main_agent_session"
    assert "official user-question" in summary["question_action"]["native_tool_policy"]
    assert summary["example_user_reply"].startswith("Build the account-deletion audit flow")
    assert (
        summary["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert "--message" in summary["debug_cli_example_command"]
    assert summary["next"].startswith("Ask the user the ask_user question")
