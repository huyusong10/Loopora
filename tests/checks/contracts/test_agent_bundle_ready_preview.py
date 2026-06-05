from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_codex_native_surface_plain,
    _assert_labeled_loopora_agent_command,
    _assert_ready_plan_payload,
    _assert_ready_plan_summary,
    _assert_ready_review_projection,
    _invoke_codex_plan,
    _write_ready_bundle,
    alignment_bundle_yaml,
    assert_agent_v3_compact_envelope,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_codex_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = _write_ready_bundle(tmp_path, sample_workdir)
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
    _assert_ready_plan_payload(payload)
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


def test_cli_codex_gen_compact_json_omits_raw_but_keeps_ready_handoff(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = _write_ready_bundle(tmp_path, sample_workdir)
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Ship contract inspection for implementation handoff.",
        bundle_file=bundle_file,
        compact_json_output=True,
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = assert_agent_v3_compact_envelope(
        payload,
        kind="agent_plan",
        summary_key="agent_plan_summary",
        status="ready",
    )
    _assert_ready_review_projection(summary["ready_review_projection"])
    surface = summary["agent_surface"]
    assert surface["entry_kind"] == "project_skill"
    assert surface["slash_commands"] == {"plan": "/loopora-plan", "run": "/loopora-run"}
    assert "loopora-builder" in surface["target_agents"]
    assert surface["capability_contract"]["role_dispatch"] == "host_native"
    assert surface["nested_provider_cli"] == "not_used"
    assert "packaging" not in surface
    assert "permission_boundary" not in surface
    assert "observability" not in surface
    assert summary["ready_slash_command"] == "/loopora-run"
    assert "loopora agent codex run" in summary["ready_cli_command"]
    assert "--json --compact-json" in summary["ready_cli_command"]


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
