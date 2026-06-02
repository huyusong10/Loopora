from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _assert_loopora_agent_command,
    assert_agent_v3_envelope,
    cli,
    json,
)


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
