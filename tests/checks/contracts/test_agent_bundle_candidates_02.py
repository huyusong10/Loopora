from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_agent_command,
    _assert_plan_message_required_summary,
    _assert_ready_plan_payload,
    _assert_ready_plan_summary,
    _assert_ready_review_projection,
    _error_text,
    _invoke_codex_plan,
    _write_ready_bundle,
    alignment_bundle_yaml,
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
    assert summary["review_status"] == "not runnable; no candidate plan file was submitted"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert summary["task_anchor_status"].startswith("task anchor preserved from /loopora-plan")
    assert summary["task_anchor_preview"].startswith("Prepare a governed implementation loop")
    assert summary["review_scope"] == "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
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
    assert "official user-question" in summary["question_action"]["native_tool_policy"]
    assert summary["example_user_reply"].startswith("Build the account-deletion audit flow")
    assert (
        summary["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert summary["next"].startswith("Ask the user the ask_user question")
    assert summary["loop_recovery"] == "plan_first"
    assert summary["next_plan_command"] == "/loopora-plan"
    assert summary["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["target"] == "main_agent_session"
    assert summary["example_user_reply"].startswith("Build the account-deletion audit flow")
    assert (
        summary["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert "--message" in summary["debug_cli_example_command"]
    assert summary["next"].startswith("Ask the user the ask_user question")


def test_cli_agent_gen_without_bundle_reports_not_fit_fallback(sample_workdir: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "There is no need for a Loopora loop here; just answer directly.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs Web review" in result.stdout
    assert "not_fit:" in result.stdout
    assert "review_status: not runnable; Loopora fit needs to be redefined" in result.stdout
    assert "review_focus:" in result.stdout
    assert "Loopora fit: define later evidence, handoffs, or GateKeeper value" in result.stdout
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only work" in result.stdout
    assert "GateKeeper value" in result.stdout
    assert "review_recommended_action: Skip Loop (Recommended)" in result.stdout
    assert "after_review_ready: return to this Agent session and run /loopora-run" in result.stdout
    _assert_codex_native_surface_plain(result.stdout)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout


def test_cli_agent_gen_without_bundle_json_reports_not_fit_fallback(sample_workdir: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "There is no need for a Loopora loop here; just answer directly.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="not_ready"
    )
    assert summary["loopora_fit_contradiction"] is True
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    _assert_codex_native_surface_summary(summary)
    assert summary["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert summary["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert summary["review_focus"][0].startswith("Loopora fit: define later evidence")
    _assert_loopora_agent_command(summary["after_review_command"], "run")


def test_cli_agent_gen_without_bundle_rejects_missing_task_summary(sample_workdir: Path) -> None:
    runner = CliRunner()

    text_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: ask one Loop-shaping question before /loopora-plan can create a preview" in text_result.stdout
    assert "next_plan_command: /loopora-plan" in text_result.stdout
    assert "required_inputs:" in text_result.stdout
    assert "- task_goal" in text_result.stdout
    assert "- fake_done_risks" in text_result.stdout
    assert "- required_evidence" in text_result.stdout
    assert "- judgment_tradeoffs" in text_result.stdout
    assert "ask_user: What long-running task should Loopora govern?" in text_result.stdout
    assert "question_action: Use the host's official user-question or follow-up capability" in text_result.stdout
    assert "recommended_reply_shape: Goal: ..." in text_result.stdout
    assert "Fake-done risks: ..." in text_result.stdout
    assert "Required evidence: ..." in text_result.stdout
    assert "Judgment tradeoffs: ..." in text_result.stdout
    assert "decision_impact: This answer decides the Loop's task contract" in text_result.stdout
    assert "example_user_reply: Build the account-deletion audit flow;" in text_result.stdout
    assert "task_message_template:" not in text_result.stdout
    assert "first_task_message_example:" not in text_result.stdout
    assert "debug_cli_example_command:" not in text_result.stdout
    _assert_codex_native_surface_plain(text_result.stdout)
    assert "next: Ask the user the ask_user question" in text_result.stdout

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

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
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert "fake done would be UI-only deletion" in summary["example_user_reply"]
    assert (
        summary["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert f"--workdir {sample_workdir.resolve()}" in summary["debug_cli_example_command"]
    assert "--message" in summary["debug_cli_example_command"]
    assert summary["next"] == "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context."


def test_agent_adapter_preview_fallback_uses_web_review_language() -> None:
    root = Path(__file__).resolve().parents[3]
    sources = "\n".join(
        [
            (root / "src" / "loopora" / "agent_adapters.py").read_text(encoding="utf-8"),
            (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(encoding="utf-8"),
            (root / "src" / "loopora" / "cli_agent_recovery.py").read_text(encoding="utf-8"),
        ]
    )

    assert "Web review" in sources
    assert "Web alignment URL" not in sources
    assert "needs Web alignment" not in sources
    assert "more alignment before" not in sources


def test_cli_codex_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file, expected = _write_ready_bundle(tmp_path, sample_workdir)
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Ship contract inspection for implementation handoff.",
        bundle_file=bundle_file,
        json_output=True,
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    _assert_ready_plan_summary(payload)
    _assert_ready_plan_payload(payload, expected)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready"
    )
    _assert_ready_review_projection(summary["ready_review_projection"])
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert summary["review_before_loop"] == "confirm the preview carries these judgments before running /loopora-run"
    assert summary["ready_next_step"].startswith("return to this Agent session and run /loopora-run")
    assert summary["ready_slash_command"] == "/loopora-run"
    assert "loopora agent codex run" in summary["ready_cli_command"]
    assert "--json" in summary["ready_cli_command"]
    assert summary["ready_run_command"] == summary["ready_cli_command"]
    assert "run" not in summary


def test_cli_agent_gen_ready_output_points_back_to_same_agent_loop(tmp_path: Path, sample_workdir: Path) -> None:
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
            "--message",
            "Ship contract inspection for implementation handoff.",
            "--bundle-file",
            str(bundle_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview is ready" in result.stdout
    assert "next_agent_step: review the preview URL, then run /loopora-run in this same Agent session" in result.stdout
    assert "ready_review:" in result.stdout
    assert "loopora_fit:" in result.stdout
    assert "fake_done_risks:" in result.stdout
    assert "evidence_preferences:" in result.stdout
    assert "coverage_targets: 2 checks /" in result.stdout
    assert "judgment_projection: 13/13 mapped" in result.stdout
    assert "closure_gate: GateKeeper (evidence_refs_required)" in result.stdout
    assert "review_before_loop: confirm the preview carries these judgments before running /loopora-run" in result.stdout
    assert "ready_next_step: return to this Agent session and run /loopora-run" in result.stdout
    assert "ready_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "ready_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "ready_run_command", "run")
    _assert_codex_native_surface_plain(result.stdout)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout
    assert "run_url:" not in result.stdout
    assert "Loopora run:" not in result.stdout


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
    assert "- task_goal" in result.stdout
    assert "- required_evidence" in result.stdout
