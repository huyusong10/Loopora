from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_labeled_loopora_agent_command,
    _assert_web_review_json_payload,
    _assert_web_review_plain_output,
    _error_text,
    _invoke_codex_plan,
    cli,
    cli_agent_runtime_support,
    json,
)


def test_cli_agent_gen_without_bundle_reports_web_alignment_needed(sample_workdir: Path) -> None:
    runner = CliRunner()
    task_message = "Prepare a governed implementation loop."

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
    )

    assert result.exit_code == 0, result.stdout
    _assert_web_review_plain_output(result.stdout, task_message=task_message)

    json_task_message = "Prepare a second governed implementation loop."
    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=json_task_message,
        entry_source="codex_project_skill",
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    _assert_web_review_json_payload(json.loads(json_result.stdout), task_message=json_task_message)


def test_cli_agent_gen_reports_auto_started_web_review_url(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9876", "reused": False, "started": True, "port": 9876},
    )

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--entry-source",
            "codex_project_skill",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs Web review" in result.stdout
    assert "review_status: not runnable; no candidate plan file was submitted" in result.stdout
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in result.stdout
    assert "review_scope: review_focus lists Loop surfaces to compile" in result.stdout
    assert "not missing chat input" in result.stdout
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in result.stdout
    assert "review_focus:" in result.stdout
    assert "preview_url: http://127.0.0.1:9876/loops/new/bundle?alignment_session_id=" in result.stdout
    assert "run_blocked_until_web_review: yes" in result.stdout
    assert "after_review_cli_command_status: blocked_until_web_review_complete" in result.stdout
    assert "after_review_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "after_web_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "after_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "after_review_command", "run")
    assert "web: started http://127.0.0.1:9876" in result.stdout


def test_cli_agent_loop_after_web_review_fallback_reprints_review_url_and_focus(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop with later evidence and GateKeeper review.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9988", "reused": False, "started": True, "port": 9988},
    )

    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir)])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    assert "loop_recovery: finish the current Web review before /loopora-run can start" in output_text
    assert "review_status: not runnable; no candidate plan file was submitted" in output_text
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in output_text
    assert "review_scope: review_focus lists Loop surfaces to compile" in output_text
    assert "not missing chat input" in output_text
    assert "review_focus:" in output_text
    assert "Success surface:" in output_text
    assert "Fake-done risks:" in output_text
    assert "Evidence expectations:" in output_text
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in output_text
    assert "next_review_step: open the preview URL" in output_text
    assert "after_review_ready: return to this Agent session and run /loopora-run" in output_text
    assert "run_blocked_until_web_review: yes" in output_text
    assert "after_review_cli_command_status: blocked_until_web_review_complete" in output_text
    assert "after_review_slash_command: /loopora-run" in output_text
    _assert_labeled_loopora_agent_command(output_text, "after_web_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(output_text, "after_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(output_text, "after_review_command", "run")
    assert "preview_url: http://127.0.0.1:9988/loops/new/bundle?alignment_session_id=" in output_text
    assert "web: started http://127.0.0.1:9988" in output_text
    assert "Traceback" not in output_text
    assert _error_text(loop_result) == ""
    assert "cli.command.failed" not in output_text
    assert "current status: idle" not in output_text
