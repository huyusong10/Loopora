from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    Path,
    _assert_invalid_candidate_repair_payload,
    _assert_invalid_candidate_repair_plain_output,
    _assert_invalid_candidate_run_recovery,
    _error_text,
    _invoke_codex_plan,
    alignment_bundle_yaml,
    assert_agent_v3_envelope,
    cli,
    cli_agent_adapter_commands,
    json,
    yaml,
)


def test_cli_agent_gen_with_invalid_candidate_reports_repair_before_loop(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    task_message = "Build a governed refund self-service flow with authorization, audit, and payment failure evidence."
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
    )

    assert result.exit_code == 0, result.stdout
    _assert_invalid_candidate_repair_plain_output(result.stdout, task_message=task_message, bundle_file=bundle_file)

    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    _assert_invalid_candidate_repair_payload(payload, task_message=task_message, bundle_file=bundle_file)
    repair_summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )

    run_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--no-web",
            "--json",
        ],
    )

    assert run_result.exit_code == 1
    assert _error_text(run_result) == ""
    _assert_invalid_candidate_run_recovery(
        run_result.stdout,
        task_message=task_message,
        validation_error=repair_summary["validation_error"],
        repair_focus=repair_summary["repair_focus"],
        bundle_file=bundle_file,
    )


def test_agent_plan_repair_focus_explains_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project explicit host Agent success criteria "
        "into runnable surfaces: missing data/export/report"
    )

    assert hints[0] == "add these missing success criteria categories from --message to runnable plan surfaces: data/export/report"
    assert hints[1] == (
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, "
        "evidence preferences, and GateKeeper closure"
    )


def test_agent_plan_repair_focus_explains_multiple_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project the host Agent task summary "
        "into runnable surfaces: missing soc2, vendor, rollout; "
        "agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: "
        "missing permission/audit, download/export-only; "
        "agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: "
        "missing audit/log, permission/auth"
    )

    assert "add these missing task objects from --message to runnable plan surfaces: soc2, vendor, rollout" in hints
    assert (
        "add these missing fake-done risks categories from --message to runnable plan surfaces: "
        "permission/audit, download/export-only"
    ) in hints
    assert (
        "add these missing evidence preferences categories from --message to runnable plan surfaces: "
        "audit/log, permission/auth"
    ) in hints
    assert "include those evidence modes in spec Evidence Preferences, Inspector responsibilities, workflow handoffs, and GateKeeper closure" in hints


def test_agent_plan_repair_focus_explains_common_semantic_lint_issues() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: "
        "collaboration_summary must explain why this task needs multi-round Loopora governance; "
        "spec must include at least one Success Surface bullet; "
        "spec Residual Risk guidance must name accepted risk handling or fail closed"
    )

    assert (
        "explain in collaboration_summary what later evidence, reviews, handoffs, or GateKeeper rounds add beyond one Agent pass"
        in hints
    )
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in hints
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in hints


def test_cli_agent_loop_plain_output_discloses_resumed_existing_run(capsys) -> None:
    cli_agent_adapter_commands._print_agent_loop_result(
        {
            "run": {"id": "run_resume", "status": "awaiting_agent"},
            "run_path": "/runs/run_resume",
            "started_new_run": False,
            "complete": False,
        },
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Loopora run: run_resume" in output
    assert "run_start: resumed_existing_agent_runner_run" in output


def test_cli_agent_gen_json_repair_focus_explains_structural_plan_errors(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bad-bundle.yml"
    bundle_file.write_text("version: 1\nspec:\n  name: Refund admin\n", encoding="utf-8")
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
            "Build a refund admin workflow with audit and provider-failure evidence.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert summary["validation_error"] == "bundle metadata.name is required"
    assert "add metadata.name so the plan has a stable reviewable identity" in summary["repair_focus"]


def test_cli_agent_gen_json_repair_focus_explains_semantic_lint_issues(tmp_path: Path, sample_workdir: Path) -> None:
    payload = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    payload["collaboration_summary"] = "Coordinate a starter slice."
    markdown = payload["spec"]["markdown"]
    markdown = markdown.replace(
        "# Success Surface\n\n- The primary user flow is understandable, maintainable, and easy to extend after the first pass.\n\n",
        "",
    )
    markdown = markdown.replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; "
        "fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk remains.",
    )
    payload["spec"]["markdown"] = markdown
    bundle_file = tmp_path / "semantic-lint-bundle.yml"
    bundle_file.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
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
            "Ship the focused starter experience in the target workdir with evidence and GateKeeper review.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    output = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        output, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert "collaboration_summary must explain the governance story" in summary["validation_error"]
    assert "spec must include at least one Success Surface bullet" in summary["validation_error"]
    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" in summary["validation_error"]
    assert "rewrite collaboration_summary with the concrete task, evidence flow, blockers, and GateKeeper closure" in summary["repair_focus"]
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in summary["repair_focus"]
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in summary["repair_focus"]


def test_cli_agent_loop_reports_candidate_repair_state_after_failed_gen(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
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
            "Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    error_text = _error_text(loop_result)
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in output_text
    assert error_text == ""
    assert "plan_file_to_repair:" in output_text
    assert "preview_plan_copy:" in output_text
    assert "repair_focus:" in output_text
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output_text
    assert "next_repair_step: repair the candidate plan file" in output_text
    assert "preserves repair_task_message and repair_focus" in output_text
    assert "project the task objects from --message" in output_text


def test_cli_agent_gen_with_candidate_not_fit_reports_reframe_before_loop(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
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
            "There is no need for a Loopora loop here; just answer directly.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in gen_result.stdout
    assert "not_fit:" in gen_result.stdout
    assert "reframe the task with later evidence, handoff, or GateKeeper value" in gen_result.stdout
    assert "Loopora is not fit" in gen_result.stdout
    assert loop_result.exit_code == 1
    error_text = _error_text(loop_result)
    assert error_text == ""
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in loop_result.output
    assert "not_fit:" in loop_result.output
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only" in loop_result.output
    assert "GateKeeper value" in loop_result.output
    assert "next_repair_step: repair the candidate plan file" in loop_result.output
    assert "preserves repair_task_message and repair_focus" in loop_result.output


def test_cli_agent_gen_uses_repair_flag_when_candidate_status_is_not_failed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()

    class FakeService:
        def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict:
            assert request.adapter == "codex"
            assert request.workdir == workdir
            assert request.message == "Repair this candidate without pretending it is runnable."
            return {
                "ready": False,
                "status": "blocked",
                "requires_web_alignment": False,
                "requires_candidate_repair": True,
                "session": {
                    "id": "session_repair",
                    "error_message": "candidate is missing required audit evidence",
                },
                "preview_path": "/loops/new/bundle?alignment_session_id=session_repair",
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(workdir),
            "--message",
            "Repair this candidate without pretending it is runnable.",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in result.stdout
    assert "needs candidate repair" not in result.stdout
    assert "validation_error: candidate is missing required audit evidence" in result.stdout
    assert "Loopora Loop preview status: blocked" not in result.stdout
