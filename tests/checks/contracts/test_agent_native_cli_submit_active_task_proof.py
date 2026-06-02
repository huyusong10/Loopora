from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    _assert_codex_native_surface_summary,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_submit_json_separates_active_step_lifecycle_from_task_proof(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_active",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "Builder submitted a non-terminal handoff."},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_active",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "task_verdict": {
                        "status": "not_evaluated",
                        "summary": "Required coverage targets still lack direct evidence.",
                    },
                },
                "run_path": "/runs/run_active",
                "next_step": {
                    "step_id": "contract_inspection_step",
                    "role": {"name": "Contract Inspector"},
                    "role_dispatch": {"target_agent": "loopora-inspector"},
                    "action_policy": {"workspace": "read_only", "can_block": True},
                    "submit_hint": {"command": "loopora agent codex submit --run-id run_active"},
                },
                "complete": False,
                "submitted_step": {
                    "step_id": "builder_step",
                    "status": "completed",
                    "summary": "Builder produced a handoff, but the task is not proven.",
                    "evidence_refs": ["ev_000_00_builder_step"],
                    "coverage_results": [
                        {
                            "target_id": "done_when.check_001",
                            "status": "covered",
                            "evidence_refs": ["ev_000_00_builder_step"],
                            "note": "Builder evidence was classified against the first target.",
                        }
                    ],
                    "blocking_items": [],
                    "recommended_next_action": "Inspect the handoff before claiming task proof.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / "run_active" / "handoff.json"),
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
            "run_active",
            "--step-id",
            "builder_step",
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
    assert summary["run_status"] == "awaiting_agent"
    assert summary["complete"] is False
    assert summary["submitted_step"]["step_id"] == "builder_step"
    assert summary["submitted_step"]["coverage_result_counts"] == {"covered": 1}
    assert summary["submitted_step"]["coverage_results"][0]["target_id"] == "done_when.check_001"
    assert summary["submitted_step"]["coverage_results"][0]["status"] == "covered"
    assert "recommended_next_action" not in summary["submitted_step"]
    assert summary["next_step"]["step_id"] == "contract_inspection_step"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_yet_evaluated"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    _assert_codex_native_surface_summary(summary)
