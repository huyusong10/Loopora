from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    Path,
    _assert_codex_native_surface_summary,
    _assert_labeled_loopora_agent_command,
    _error_text,
    alignment_bundle_yaml,
    cli,
    json,
)


def test_cli_agent_next_without_exact_binding_reports_direct_run_recovery(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id="thread-original",
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-original",
        entry_source="codex_project_skill",
        execute_async=False,
    )
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
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
        payload, kind="agent_recovery", summary_key="agent_next_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "choose_recoverable_context"
    _assert_codex_native_surface_summary(summary)
    assert summary["choice_count"] == 1
    assert summary["runnable_choice_count"] == 1
    assert summary["next_active_run_command"].endswith(
        f"--run-id {started['run']['id']} --json --compact-json --entry-source codex_project_skill"
    )
    assert summary["choices"][0]["choice_status"] == "active_run"
    assert summary["choices"][0]["next_agent_command"].endswith(
        f"--run-id {started['run']['id']} --json --compact-json --entry-source codex_project_skill"
    )
    assert summary["loop_recovery"] == "choose_recoverable_context"
    assert summary["choices"][0]["linked_run_id"] == started["run"]["id"]
    assert summary["choices"][0]["next_agent_command"].endswith(
        f"--run-id {started['run']['id']} --json --compact-json --entry-source codex_project_skill"
    )

    text_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: choose a recoverable Loopora context before claiming the next Agent step" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_active_run_command", "next")
    assert f"--run-id {started['run']['id']}" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_agent_command", "next")
    assert "for an already active run, run its next_agent_command to claim the current step" in text_result.stdout
