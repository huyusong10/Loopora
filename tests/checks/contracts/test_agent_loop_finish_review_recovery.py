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


def test_cli_agent_loop_json_after_web_review_fallback_returns_structured_recovery(sample_workdir: Path) -> None:
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

    loop_result = runner.invoke(
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

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    assert _error_text(loop_result) == ""
    payload = json.loads(loop_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["review_status"] == "not runnable; no candidate plan file was submitted"
    assert summary["task_anchor_status"].startswith("task anchor preserved from /loopora-plan")
    assert summary["review_scope"] == (
        "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
    )
    assert summary["loop_recovery"] == "finish_web_review"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert summary["task_anchor_preview"].startswith("Prepare a governed implementation loop")
    assert summary["after_review_slash_command"] == "/loopora-run"
    _assert_loopora_agent_command(summary["after_review_cli_command"], "run")


def test_cli_agent_loop_selected_not_ready_option_returns_current_context_command(sample_workdir: Path) -> None:
    runner = CliRunner()
    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-original-review",
            "--message",
            "Prepare a governed implementation loop with later evidence and GateKeeper review.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )
    assert gen_result.exit_code == 0, gen_result.stdout
    generated = json.loads(gen_result.stdout)
    generated_summary, _legacy = assert_agent_v3_envelope(
        generated, kind="agent_plan", summary_key="agent_plan_summary", status="not_ready"
    )
    option_id = f"agent_run:{generated['raw']['legacy']['session']['id']}"
    assert generated_summary["after_review_slash_command"] == "/loopora-run"
    assert "--context-id thread-original-review" in generated_summary["after_review_cli_command"]
    assert "--context-id thread-original-review" in generated_summary["after_review_command"]

    loop_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-selected-review",
            "--source-option-id",
            option_id,
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert loop_result.exit_code == 1
    assert _error_text(loop_result) == ""
    payload = json.loads(loop_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "finish_web_review"
    assert summary["after_review_slash_command"] == "/loopora-run"
    assert "--context-id thread-selected-review" in summary["after_review_cli_command"]
    assert "--context-id thread-original-review" not in summary["after_review_cli_command"]
