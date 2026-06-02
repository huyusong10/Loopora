from __future__ import annotations

from agent_native_cli_test_support import (
    CliRunner,
    Path,
    RunArtifactLayout,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _mkdir,
    _terminal_unproven_loop_payload,
    _write_terminal_unproven_run_contract,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_loop_terminal_unproven_reports_lifecycle_without_complete(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LOOPORA_AGENT_ENTRY_SOURCE", raising=False)
    workdir = _mkdir(tmp_path / "project")
    expected_workdir = workdir
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal_loop")
    _write_terminal_unproven_run_contract(layout)

    class FakeService:
        def start_agent_loop(
            self,
            _adapter: str,
            *,
            workdir: Path,
            context_id: str = "",
            entry_source: str = "",
            execute_async: bool = True,
        ):
            assert _adapter == "codex"
            assert workdir == expected_workdir
            assert context_id == "thread-1"
            assert entry_source == ""
            assert execute_async is False
            return _terminal_unproven_loop_payload(layout)

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(workdir), "--context-id", "thread-1", "--no-web"],
    )

    assert result.exit_code == 0, result.stdout
    assert "run_status: succeeded" in result.stdout
    assert "run_start: replayed_existing_terminal_run" in result.stdout
    _assert_codex_native_surface_plain(result.stdout)
    assert f"run_contract_path: {layout.run_contract_path}" in result.stdout
    assert "task_verdict: insufficient_evidence" in result.stdout
    assert "task_next_action: Run lifecycle is complete, but the task is not proven." in result.stdout
    assert "next_loop_command: /loopora-run" in result.stdout
    assert "next_evidence_focus: Audit proof is still missing." in result.stdout
    assert "agent_runner: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_runner_task_verdict: insufficient_evidence" in result.stdout
    assert "task_proof_source: run.task_verdict" in result.stdout
    assert "run_lifecycle_source: result.complete" in result.stdout
    assert "agent_runner: complete" not in result.stdout


def test_cli_agent_loop_json_reports_terminal_task_proof_summary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LOOPORA_AGENT_ENTRY_SOURCE", raising=False)
    workdir = tmp_path / "project"
    workdir.mkdir()
    expected_workdir = workdir
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal_loop")
    _write_terminal_unproven_run_contract(layout)

    class FakeService:
        def start_agent_loop(
            self,
            _adapter: str,
            *,
            workdir: Path,
            context_id: str = "",
            entry_source: str = "",
            execute_async: bool = True,
        ):
            assert _adapter == "codex"
            assert workdir == expected_workdir
            assert context_id == "thread-1"
            assert entry_source == ""
            assert execute_async is False
            return _terminal_unproven_loop_payload(layout)

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(workdir), "--context-id", "thread-1", "--no-web", "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_run", summary_key="agent_run_summary", status="complete"
    )
    assert summary["run_id"] == "run_terminal_loop"
    assert summary["run_status"] == "succeeded"
    assert summary["complete"] is True
    assert summary["task_verdict_status"] == "insufficient_evidence"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_complete_task_not_proven"
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_evidence_focus"] == "Audit proof is still missing."
    panel = summary["agent_work_panel"]
    assert list(panel) == [
        "state",
        "run_id",
        "task_proven",
        "task_outcome",
        "current_role",
        "current_step_id",
        "next_action",
        "evidence_focus",
        "top_gaps",
        "ask_user",
        "todo_items",
        "run_url",
    ]
    assert panel["state"] == "needs_more_evidence"
    assert panel["run_id"] == "run_terminal_loop"
    assert panel["task_proven"] is False
    assert panel["task_outcome"] == "not_proven_continue_evidence"
    assert panel["next_action"] == "Task proof is still missing; run /loopora-run again in this Agent session to continue evidence."
    assert panel["evidence_focus"] == "Audit proof is still missing."
    assert "next_step" not in summary
    _assert_codex_native_surface_summary(summary)
