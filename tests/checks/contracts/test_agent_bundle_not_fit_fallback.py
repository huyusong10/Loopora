from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_codex_native_surface_summary,
    assert_agent_v3_envelope,
    cli,
    json,
)
from agent_adapter_test_common import _labeled_value


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
    assert "Loopora fit needs a user decision before generating a runnable Loop" in result.stdout
    assert "not_fit:" in result.stdout
    assert "review_status: not runnable; Loopora fit needs to be redefined" in result.stdout
    assert "review_focus:" in result.stdout
    assert "Loopora fit: define later evidence, handoffs, or GateKeeper value" in result.stdout
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only work" in result.stdout
    assert "GateKeeper value" in result.stdout
    assert "review_recommended_action: Skip Loop (Recommended)" in result.stdout
    assert "next_review_step: reply with review_reply_preview to skip Loop generation" in result.stdout
    assert result.stdout.index("review_focus:") < result.stdout.index("next_review_step:")
    assert "next_plan_cli_command_policy: fallback_for_non_interactive_agents" in result.stdout
    assert result.stdout.index("next_review_step:") < result.stdout.index("preview_url:")
    assert "preview_url_status: relative_path_web_not_started" in result.stdout
    assert _labeled_value(result.stdout, "preview_url_web_start_command").endswith(
        f"loopora serve --open --workdir {sample_workdir.resolve()} --host 127.0.0.1 --port 8742"
    )
    assert result.stdout.index("preview_url:") < result.stdout.index("preview_url_status:")
    assert result.stdout.index("preview_url_status:") < result.stdout.index("preview_url_web_start_command:")
    assert result.stdout.index("preview_url_web_start_command:") < result.stdout.index("next_plan_cli_command_policy:")
    assert result.stdout.index("next_plan_cli_command_policy:") < result.stdout.index("next_plan_cli_command:")
    assert "after_review_ready:" not in result.stdout
    assert "after_review_cli_command:" not in result.stdout
    assert "agent_surface: current host Agent remains the executor" in result.stdout
    assert "full surface diagnostics are available with --json --compact-json" in result.stdout
    assert "agent surface:" not in result.stdout
    assert "- host dispatch:" not in result.stdout
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout
    assert result.stdout.count("preview_url:") == 1


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
    assert summary["preview_url_status"] == "relative_path_web_not_started"
    assert summary["preview_url_web_start_command"].endswith(
        f"loopora serve --open --workdir {sample_workdir.resolve()} --host 127.0.0.1 --port 8742"
    )
    _assert_codex_native_surface_summary(summary)
    assert summary["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert summary["review_focus"][0].startswith("Loopora fit: define later evidence")
    assert summary["next_review_step"].startswith("reply with review_reply_preview")
    assert "after_review_command" not in summary
    assert "after_review_cli_command" not in summary


def test_cli_agent_gen_without_bundle_treats_benchmark_only_acceptance_as_not_fit(sample_workdir: Path) -> None:
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
            "请帮我优化 JSON parser 的性能，只要现有 benchmark 和单元测试全部通过就算完成；没有额外产品判断。也请生成 Loopora plan。",
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
    assert summary["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert summary["review_recommended_action"] == "先不生成 Loop（推荐）"
    assert summary["review_focus"][0].startswith("Loopora fit: define later evidence")
    assert "同意，先不生成 Loop 方案" in summary["review_reply_preview"]
    assert "只要现有 benchmark 和单元测试全部通过就算完成" in summary["review_reply_preview"]


def test_cli_agent_gen_not_fit_skip_reply_is_terminal(sample_workdir: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"LOOPORA_HOME": str(tmp_path / "home")}
    context_id = "not-fit-skip-terminal"
    first = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            context_id,
            "--message",
            "请帮我把 README 里的一个错别字修掉。只要现有检查通过就算完成；这是一次性小修，不需要后续轮次或新证据。",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
            "--compact-json",
        ],
        env=env,
    )

    assert first.exit_code == 0, first.stdout
    first_payload = json.loads(first.stdout)
    assert first_payload["kind"] == "agent_plan"
    assert first_payload["status"] == "not_ready"
    first_summary = first_payload["summary"]

    skipped = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            context_id,
            "--message",
            first_summary["review_reply_preview"],
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
            "--compact-json",
        ],
        env=env,
    )

    assert skipped.exit_code == 0, skipped.stdout
    skipped_payload = json.loads(skipped.stdout)
    assert skipped_payload["kind"] == "agent_plan"
    assert skipped_payload["status"] == "not_ready"
    summary = skipped_payload["summary"]
    assert summary["status"] == "skipped"
    assert summary["loop_recovery"] == "alignment_skipped"
    assert summary["requires_web_alignment"] is False
    assert "不会写入 bundle，也不会启动运行" in summary["alignment_assistant_message"]
    assert "next_alignment_step" not in summary
    assert "preview_url" not in summary
    assert "after_review_command" not in summary


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
