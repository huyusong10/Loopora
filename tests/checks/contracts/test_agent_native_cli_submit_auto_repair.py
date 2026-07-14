from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    _agent_submit_auto_repair_success_payload,
    _invoke_codex_submit,
    _write_agent_submit_auto_repair_fixture,
    assert_agent_v3_envelope,
    cli,
    json,
)


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

    legacy_result = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=direct_result_file,
        json_output=True,
    )
    explicit_result = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=direct_result_file,
        json_output=True,
        attest_role_dispatch=True,
    )

    assert legacy_result.exit_code == 0, legacy_result.stdout
    assert explicit_result.exit_code == 0, explicit_result.stdout
    assert captured_requests[0].output == {"summary": "Builder produced direct proof."}
    assert captured_requests[0].host_dispatch["run_id"] == "run_auto_repair"
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-builder"
    assert captured_requests[0].host_dispatch["attestation_source"] == "legacy_template_auto_repair"
    assert captured_requests[1].host_dispatch["attestation_source"] == "explicit_submit_flag"
    legacy_payload = json.loads(legacy_result.stdout)
    legacy_summary, _legacy = assert_agent_v3_envelope(
        legacy_payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    explicit_payload = json.loads(explicit_result.stdout)
    explicit_summary, _legacy = assert_agent_v3_envelope(
        explicit_payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    assert legacy_summary["auto_repair_applied"] is True
    assert legacy_summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert legacy_summary["host_dispatch_attestation_source"] == "legacy_template_auto_repair"
    assert legacy_summary["agent_work_panel"]["state"] == "awaiting_agent"
    assert explicit_summary["auto_repair_applied"] is True
    assert explicit_summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert explicit_summary["host_dispatch_attestation_source"] == "explicit_submit_flag"


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
