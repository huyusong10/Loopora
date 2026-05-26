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
    agent_work_panel,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_loop_terminal_unproven_reports_lifecycle_without_complete(monkeypatch, tmp_path: Path) -> None:
    workdir = _mkdir(tmp_path / "project")
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal_loop")
    _write_terminal_unproven_run_contract(layout)

    class FakeService:
        def start_agent_loop(self, _adapter: str, *, workdir: Path, context_id: str = "", entry_source: str = "", execute_async: bool = True):
            _ = (workdir, context_id, entry_source, execute_async)
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
    assert "agent_native: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_native_task_verdict: insufficient_evidence" in result.stdout
    assert "task_proof_source: run.task_verdict" in result.stdout
    assert "run_lifecycle_source: result.complete" in result.stdout
    assert "agent_native: complete" not in result.stdout


def test_cli_agent_loop_json_reports_terminal_task_proof_summary(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal_loop")
    _write_terminal_unproven_run_contract(layout)

    class FakeService:
        def start_agent_loop(self, _adapter: str, *, workdir: Path, context_id: str = "", entry_source: str = "", execute_async: bool = True):
            _ = (workdir, context_id, entry_source, execute_async)
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


def test_agent_work_panel_prioritizes_dispatch_repair_before_submitted_blocker() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "not_evaluated"}},
            "next_step": {
                "step_id": "builder_step",
                "role": {"name": "Builder"},
                "role_dispatch": {
                    "target_agent": "loopora-builder",
                    "target_agent_config_exists": False,
                    "target_agent_config_path": ".codex/agents/loopora-builder.toml",
                },
                "submit_hint": {"command": "loopora agent codex submit --run-id run_panel"},
            },
            "submitted_step": {
                "step_id": "gatekeeper_step",
                "status": "blocked",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "No action needed.",
            },
            "adapter": "codex",
            "workdir": "/tmp/project",
        }
    )

    assert panel["state"] == "dispatch_unavailable"
    assert "repair the managed role agent config" in panel["next_action"]


def test_agent_work_panel_derives_blocked_submit_action_from_blocker() -> None:
    panel = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "failed"}},
            "submitted_step": {
                "step_id": "gatekeeper_step",
                "status": "blocked",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "No action needed.",
            },
        }
    )

    assert panel["state"] == "blocked"
    assert panel["next_action"].startswith("Produce new project-owned proof")
    assert "No action needed" not in panel["next_action"]
