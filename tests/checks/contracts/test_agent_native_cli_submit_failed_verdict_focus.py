from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_submit_json_marks_active_failed_verdict_as_continue_evidence(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_active_failed",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"passed": True},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_active_failed",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "task_verdict": {
                        "status": "failed",
                        "summary": "GateKeeper rejected the pass because cited evidence was non-supporting.",
                    },
                },
                "run_path": "/runs/run_active_failed",
                "next_step": {
                    "step_id": "builder_step",
                    "role": {"name": "Builder"},
                    "role_dispatch": {"target_agent": "loopora-builder"},
                    "action_policy": {"workspace": "workspace_write"},
                    "submit_hint": {"command": "loopora agent codex submit --run-id run_active_failed"},
                },
                "complete": False,
                "submitted_step": {
                    "step_id": "gatekeeper_step",
                    "status": "blocked",
                    "summary": "GateKeeper blocked the pass.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                    "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                    "recommended_next_action": "No action needed.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / "run_active_failed" / "handoff.json"),
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_active_failed",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    assert summary["complete"] is False
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["next_evidence_focus"] == "GateKeeper rejected the pass because cited evidence was non-supporting."
    assert summary["submitted_step"]["recommended_next_action"].startswith("Produce new project-owned proof")
