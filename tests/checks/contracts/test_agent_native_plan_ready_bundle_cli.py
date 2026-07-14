from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import CliRunner, Path, alignment_bundle_yaml, cli, json
from loopora.service_agent_adapters import AgentBundleCandidateRequest


def test_confirmed_candidate_validation_never_constructs_alignment_executor(
    tmp_path: Path,
    sample_workdir: Path,
    service_factory,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service = service_factory()

    def forbidden_executor() -> None:
        raise AssertionError("confirmed candidate validation must not construct an alignment executor")

    service.executor_factory = forbidden_executor
    result = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare the confirmed governed implementation loop.",
            bundle_file=bundle_file,
            context_id="codex-confirmed-candidate",
            entry_source="codex_project_skill",
        )
    )

    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["requires_web_alignment"] is False


def test_cli_claude_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "claude",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--context-id",
            "claude-session-a",
            "--entry-source",
            "claude_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True
    assert summary["status"] == "ready"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in summary


def test_cli_agent_runtime_accepts_managed_entry_source_from_env(monkeypatch, tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("LOOPORA_AGENT_ENTRY_SOURCE", "claude_project_skill")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "claude",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--context-id",
            "claude-session-a",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True


def test_cli_opencode_gen_accepts_ready_bundle_without_starting_run(monkeypatch, tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-thread-must-not-bind-opencode")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "opencode",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--entry-source",
            "opencode_project_command",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True
    assert summary["status"] == "ready"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in summary
