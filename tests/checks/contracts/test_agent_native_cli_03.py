from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    _agent_submit_auto_repair_success_payload,
    _assert_codex_native_surface_summary,
    _invoke_codex_submit,
    _write_agent_submit_auto_repair_fixture,
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


def test_cli_agent_submit_auto_repairs_missing_wrapper_from_active_template(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_agent_submit_auto_repair_fixture(tmp_path)
    direct_result_file = fixture["workdir"] / "direct-result.json"
    direct_result_file.write_text(json.dumps({"summary": "Builder produced direct proof."}), encoding="utf-8")

    captured_requests: list[AgentNativeStepSubmitRequest] = []

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_auto_repair"
            return {"id": run_id, "runs_dir": str(fixture["layout"].run_dir)}

        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            captured_requests.append(request)
            return _agent_submit_auto_repair_success_payload(fixture, request)

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=direct_result_file,
        json_output=True,
    )

    assert result.exit_code == 0, result.stdout
    assert captured_requests[0].output == {"summary": "Builder produced direct proof."}
    assert captured_requests[0].host_dispatch["run_id"] == "run_auto_repair"
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-builder"
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    assert summary["auto_repair_applied"] is True
    assert summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert summary["agent_work_panel"]["state"] == "awaiting_agent"
    assert summary["auto_repair_applied"] is True


def test_cli_agent_submit_auto_repairs_result_only_wrapper_and_template_path(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_agent_submit_auto_repair_fixture(tmp_path)
    result_only_file = fixture["workdir"] / "result-only.json"
    result_only_file.write_text(json.dumps({"result": {"summary": "Builder filled result only."}}), encoding="utf-8")
    template_file = fixture["active_template"]
    template_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": fixture["host_dispatch"],
                "result": {"summary": "Builder filled the template path."},
            }
        ),
        encoding="utf-8",
    )
    captured_requests: list[AgentNativeStepSubmitRequest] = []

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_auto_repair"
            return {"id": run_id, "runs_dir": str(fixture["layout"].run_dir)}

        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            captured_requests.append(request)
            return _agent_submit_auto_repair_success_payload(fixture, request)

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    restored = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=result_only_file,
        json_output=True,
    )
    template_path = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=template_file,
        json_output=False,
    )

    assert restored.exit_code == 0, restored.stdout
    restored_payload = json.loads(restored.stdout)
    restored_summary, _legacy = assert_agent_v3_envelope(
        restored_payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    assert restored_summary["auto_repair_actions"] == [
        "restored_loopora_host_dispatch_from_active_template"
    ]
    assert captured_requests[0].output == {"summary": "Builder filled result only."}
    assert captured_requests[0].host_dispatch["step_id"] == "builder_step"

    assert template_path.exit_code == 0, template_path.stdout
    assert "auto_repair: submitted result format repaired before submit" in template_path.stdout
    assert "accepted_filled_result_template_path_as_result_file" in template_path.stdout
    assert captured_requests[1].output == {"summary": "Builder filled the template path."}
