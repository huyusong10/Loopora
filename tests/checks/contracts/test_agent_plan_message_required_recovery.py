from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_loopora_agent_command,
    _assert_plan_message_required_summary,
    _error_text,
    alignment_bundle_yaml,
    assert_agent_v3_envelope,
    cli,
    json,
)


def _plan_message_required_args(sample_workdir: Path) -> list[str]:
    return [
        "agent",
        "codex",
        "plan",
        "--workdir",
        str(sample_workdir),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]


def test_cli_agent_gen_without_bundle_plain_output_asks_one_question(sample_workdir: Path) -> None:
    runner = CliRunner()

    text_result = runner.invoke(cli.app, _plan_message_required_args(sample_workdir))

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: ask one Loop-shaping question before /loopora-plan can create a preview" in text_result.stdout
    assert "next_plan_command: /loopora-plan" in text_result.stdout
    assert "required_inputs:" in text_result.stdout
    assert "- Loopora fit reason (loopora_fit_reason)" in text_result.stdout
    assert "- Task goal (task_goal)" in text_result.stdout
    assert "- Fake-done risks (fake_done_risks)" in text_result.stdout
    assert "- Required evidence (required_evidence)" in text_result.stdout
    assert "- Judgment tradeoffs (judgment_tradeoffs)" in text_result.stdout
    assert "ask_user: What long-running task should Loopora govern?" in text_result.stdout
    assert "question_action: Use the host's official user-question or follow-up capability" in text_result.stdout
    assert "recommended_reply_shape: Loopora fit: ..." in text_result.stdout
    assert "Goal: ..." in text_result.stdout
    assert "Fake-done risks: ..." in text_result.stdout
    assert "Required evidence: ..." in text_result.stdout
    assert "Judgment tradeoffs: ..." in text_result.stdout
    assert "decision_impact: This answer decides the Loop's task contract" in text_result.stdout
    assert "example_user_reply: Loopora fit:" in text_result.stdout
    _assert_plain_message_cli_command(text_result.stdout)
    assert "task_message_template:" not in text_result.stdout
    assert "first_task_message_example:" not in text_result.stdout
    assert "debug_cli_example_command:" not in text_result.stdout
    assert "agent_surface: current host Agent remains the executor" in text_result.stdout
    assert "full surface diagnostics are available with --json --compact-json" in text_result.stdout
    assert "agent surface:" not in text_result.stdout
    assert "- host dispatch:" not in text_result.stdout
    assert "next: Ask the user the ask_user question" in text_result.stdout


def test_cli_agent_gen_without_bundle_json_preserves_machine_recovery(
    sample_workdir: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    loopora_home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    runner = CliRunner()

    json_result = runner.invoke(cli.app, [*_plan_message_required_args(sample_workdir), "--json"])

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="not_ready"
    )
    _assert_plan_message_required_summary(summary)
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "plan_message_required"
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
    assert summary["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert "Fake-done risks: UI-only deletion" in summary["example_user_reply"]
    assert summary["message_source_policy"].startswith("If the current host user prompt already contains")
    assert "Loopora fit reason" in summary["message_source_policy"]
    _assert_loopora_agent_command(summary["message_cli_command"], "plan")
    assert "--json --compact-json" in summary["message_cli_command"]
    assert summary["next_plan_cli_command"] == summary["message_cli_command"]
    assert (
        summary["task_message_template"]
        == "Loopora fit: ...; Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert summary["first_task_message_example_state"]["copy_allowed"] is False
    assert summary["first_task_message_example_state"]["source"] == "generic_example"
    assert summary["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert summary["first_task_handoff_policy"]["fallback_source"] == "generic_example"
    assert summary["first_task_handoff_policy"]["fit_command"].endswith(
        f"loopora fit --workdir {sample_workdir.resolve()}"
    )
    assert summary["first_task_handoff_policy"]["fit_command"].startswith(f"LOOPORA_HOME={loopora_home.resolve()} ")
    assert summary["first_task_handoff_policy"]["fit_command"] in summary["first_task_handoff_policy"]["copy_rule"]
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert f"--workdir {sample_workdir.resolve()}" in summary["debug_cli_example_command"]
    assert "--message" in summary["debug_cli_example_command"]
    assert summary["next"] == "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context."


def _assert_plain_message_cli_command(output: str) -> None:
    assert "message_source_policy: If the current host user prompt already contains" in output
    assert "message_cli_command:" in output
    message_cli = next(
        line.removeprefix("message_cli_command: ")
        for line in output.splitlines()
        if line.startswith("message_cli_command: ")
    )
    _assert_loopora_agent_command(message_cli, "plan")
    assert "--message" in message_cli
    assert "--json --compact-json" in message_cli


def test_cli_agent_gen_rejects_candidate_bundle_without_task_summary(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    assert "loop_recovery: ask one Loop-shaping question before /loopora-plan can create a preview" in result.stdout
    assert "required_inputs:" in result.stdout
    assert "- Task goal (task_goal)" in result.stdout
    assert "- Required evidence (required_evidence)" in result.stdout


def test_cli_agent_gen_message_required_precedes_candidate_file_repair(tmp_path: Path, sample_workdir: Path) -> None:
    missing_bundle_file = tmp_path / "missing-bundle.yml"
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--bundle-file",
            str(missing_bundle_file),
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
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="not_ready"
    )
    _assert_plan_message_required_summary(summary)
    assert summary["loop_recovery"] == "plan_message_required"
    assert "validation_error" not in summary
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "bundle file does not exist" not in encoded
    assert "repair_candidate_plan_file" not in encoded
