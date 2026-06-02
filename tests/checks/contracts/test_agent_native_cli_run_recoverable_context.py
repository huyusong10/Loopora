from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    Path,
    _assert_codex_native_surface_summary,
    _error_text,
    alignment_bundle_yaml,
    cli,
    json,
)


def test_cli_agent_run_without_exact_binding_reports_recoverable_context(
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
        ["agent", "codex", "run", "--workdir", str(sample_workdir), "--context-id", "thread-new", "--no-web", "--json"],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "choose_recoverable_context"
    _assert_codex_native_surface_summary(summary)
    assert summary["choice_count"] == 1
    assert summary["runnable_choice_count"] == 1
    assert summary["non_runnable_choice_count"] == 0
    assert "one runnable context is available" in summary["selection_hint"]
    assert summary["choices"][0]["choice_status"] == "active_run"
    assert summary["choices"][0]["choice_hint"].startswith("Continue the in-progress run")
    assert summary["choices"][0]["next_loop_command"].startswith("/loopora-run option:agent_run:")
    assert "--source-option-id agent_run:" in summary["choices"][0]["next_cli_command"]
    assert summary["loop_recovery"] == "choose_recoverable_context"
    assert summary["choices"][0]["linked_run_id"] == started["run"]["id"]
    assert summary["choices"][0]["runnable"] is True

    text_result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(sample_workdir), "--context-id", "thread-new", "--no-web"],
    )

    assert text_result.exit_code == 1
    assert "loop_recovery: choose a recoverable Loopora context before /loopora-run can start" in text_result.stdout
    assert "context_choices: 1 total / 1 runnable / 0 non-runnable" in text_result.stdout
    assert "choice_status: active_run" in text_result.stdout
    assert "choice_hint: Continue the in-progress run" in text_result.stdout
    assert "runnable: true" in text_result.stdout
    assert "alignment_status: running_loop" in text_result.stdout
    assert "updated_at: " in text_result.stdout
    assert "next_loop_command: /loopora-run option:agent_run:" in text_result.stdout
    assert "next_cli_command: " in text_result.stdout
    assert "--source-option-id agent_run:" in text_result.stdout
    assert "for a runnable choice, paste one next_loop_command back to the Agent" in text_result.stdout
