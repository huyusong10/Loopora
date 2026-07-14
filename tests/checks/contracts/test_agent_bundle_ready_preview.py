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
from agent_adapter_test_common import _labeled_value


READY_TASK_ANCHOR = (
    "Confirmed working agreement: preserve payment callback idempotency, rollback, audit semantics, "
    "and fail closed on double ledger writes or missing reconciliation evidence."
)
READY_REVIEW_INSTRUCTION = (
    "confirm the candidate task scope and judgments match task_anchor before running /loopora-run"
)


def _assert_ready_task_comparison(summary: dict) -> None:
    assert summary["ready_meaning"].startswith("candidate contract passed Loopora Core validation")
    assert "does not prove" in summary["ready_meaning"]
    assert summary["task_anchor_status"].startswith("preserved from the first /loopora-plan user message")
    assert summary["task_anchor"] == READY_TASK_ANCHOR
    assert "compare task_anchor with ready_review_projection.task_scope" in summary["review_scope"]
    candidate_scope = " ".join(summary["ready_review_projection"]["task_scope"])
    assert "focused starter" in candidate_scope
    assert "payment callback" not in candidate_scope.lower()
    assert summary["review_before_loop"] == READY_REVIEW_INSTRUCTION


def test_cli_codex_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = _write_ready_bundle(tmp_path, sample_workdir)
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=READY_TASK_ANCHOR,
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
    _assert_ready_task_comparison(summary)
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert summary["ready_next_step"].startswith("compare task_anchor with the candidate task scope")
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
        message=READY_TASK_ANCHOR,
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
    _assert_ready_task_comparison(summary)
    surface = summary["agent_surface"]
    assert surface["entry_kind"] == "project_skill"
    assert "slash_commands" not in surface
    assert "target_agents" not in surface
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
            READY_TASK_ANCHOR,
            "--bundle-file",
            str(bundle_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview is ready" in result.stdout
    assert "ready_meaning: candidate contract passed Loopora Core validation" in result.stdout
    assert f"task_anchor: {READY_TASK_ANCHOR}" in result.stdout
    assert "review_scope: compare task_anchor with ready_review_projection.task_scope" in result.stdout
    assert "next_agent_step: compare task_anchor with the candidate task scope" in result.stdout
    assert "ready_review:" in result.stdout
    assert "loopora_fit:" in result.stdout
    assert "fake_done_risks:" in result.stdout
    assert "evidence_preferences:" in result.stdout
    assert "coverage_targets: 2 checks /" in result.stdout
    assert "judgment_projection: 13/13 mapped" in result.stdout
    assert "closure_gate: GateKeeper (evidence_refs_required)" in result.stdout
    assert f"review_before_loop: {READY_REVIEW_INSTRUCTION}" in result.stdout
    assert "ready_next_step: compare task_anchor with the candidate task scope" in result.stdout
    assert "ready_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "ready_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "ready_run_command", "run")
    _assert_codex_native_surface_plain(result.stdout)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout
    assert "preview_url_status: relative_path_web_not_started" in result.stdout
    assert _labeled_value(result.stdout, "preview_url_web_start_command").endswith(
        f"loopora serve --open --workdir {sample_workdir.resolve()} --host 127.0.0.1 --port 8742"
    )
    assert "run_url:" not in result.stdout
    assert "Loopora run:" not in result.stdout
    assert result.stdout.index("ready_meaning:") < result.stdout.index("task_anchor:")
    assert result.stdout.index("task_anchor:") < result.stdout.index("ready_review:")
    assert result.stdout.index("ready_review:") < result.stdout.index("review_before_loop:")
    assert result.stdout.index("review_before_loop:") < result.stdout.index("ready_next_step:")
