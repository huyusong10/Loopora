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
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    monkeypatch.setattr(cli, "create_service", lambda: service)
    loopora_home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
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
    assert summary["required_inputs"] == [
        "loopora_fit_reason",
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert "Loopora fit reason" in summary["ask_user"]
    assert summary["question_action"]["kind"] == "ask_user"
    assert summary["question_action"]["target"] == "main_agent_session"
    assert "official user-question" in summary["question_action"]["native_tool_policy"]
    assert summary["example_user_reply"].startswith("Loopora fit:")
    assert summary["message_source_policy"].startswith("If the current host user prompt already contains")
    assert "Loopora fit reason" in summary["message_source_policy"]
    _assert_loopora_agent_command(summary["message_cli_command"], "plan")
    assert "--message" in summary["message_cli_command"]
    assert "--json --compact-json" in summary["message_cli_command"]
    assert summary["next_plan_cli_command"] == summary["message_cli_command"]
    assert (
        summary["task_message_template"]
        == "Loopora fit: ...; Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert summary["first_task_message_example_state"]["copy_allowed"] is False
    assert summary["first_task_message_example_state"]["kind"] == "generic_orientation_example"
    assert summary["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert summary["first_task_handoff_policy"]["fallback_source"] == "generic_example"
    assert summary["first_task_handoff_policy"]["fit_command"].startswith(f"LOOPORA_HOME={loopora_home.resolve()} ")
    assert summary["first_task_handoff_policy"]["fit_command"].endswith(
        f"loopora fit --workdir {sample_workdir.resolve()}"
    )
    assert summary["first_task_handoff_policy"]["fit_command"] in summary["first_task_handoff_policy"]["copy_rule"]
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert "--message" in summary["debug_cli_example_command"]
    assert summary["next"].startswith("Ask the user the ask_user question")


def test_cli_agent_loop_plain_without_plan_stays_question_first(
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
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    assert "loop_recovery: run /loopora-plan before /loopora-run can start" in result.stdout
    assert "ask_user: What long-running task should Loopora govern?" in result.stdout
    assert "message_cli_command:" in result.stdout
    assert "agent_surface: current host Agent remains the executor" in result.stdout
    assert "full surface diagnostics are available with --json --compact-json" in result.stdout
    assert "task_message_template:" not in result.stdout
    assert "first_task_message_example:" not in result.stdout
    assert "debug_cli_example_command:" not in result.stdout
    assert "agent surface:" not in result.stdout
