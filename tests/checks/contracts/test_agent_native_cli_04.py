from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    RunArtifactLayout,
    _assert_labeled_loopora_agent_command,
    _error_text,
    _invoke_codex_submit,
    _write_agent_submit_auto_repair_fixture,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_submit_auto_repair_keeps_core_blockers_authoritative(monkeypatch, tmp_path: Path) -> None:  # noqa: PLR0915
    fixture = _write_agent_submit_auto_repair_fixture(tmp_path)
    evidence_file = fixture["workdir"] / "unknown-evidence.json"
    evidence_file.write_text(json.dumps({"summary": "Bad evidence refs.", "evidence_refs": ["invented_ev"]}), encoding="utf-8")
    schema_file = fixture["workdir"] / "schema-mismatch.json"
    schema_file.write_text(json.dumps({"summary": 123}), encoding="utf-8")
    mismatch_file = fixture["workdir"] / "dispatch-mismatch.json"
    mismatch_dispatch = dict(fixture["host_dispatch"], actual_agent="loopora-gatekeeper")
    mismatch_file.write_text(
        json.dumps({"loopora_host_dispatch": mismatch_dispatch, "result": {"summary": "Wrong agent."}}),
        encoding="utf-8",
    )
    captured_requests: list[AgentNativeStepSubmitRequest] = []

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_auto_repair"
            return {"id": run_id, "runs_dir": str(fixture["layout"].run_dir)}

        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            captured_requests.append(request)
            if request.output.get("evidence_refs") == ["invented_ev"]:
                raise LooporaError("agent-native evidence_refs_unknown: invented_ev")
            if request.output.get("summary") == 123:
                raise LooporaConflictError("agent-native result does not match output_schema: $.summary expected string")
            raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    evidence = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=evidence_file,
        json_output=True,
    )
    schema = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=schema_file,
        json_output=True,
    )
    mismatch = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=mismatch_file,
        json_output=True,
    )
    evidence_plain = _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_auto_repair",
        step_id="builder_step",
        result_file=evidence_file,
        json_output=False,
    )

    assert evidence.exit_code == 1
    evidence_payload = json.loads(evidence.stdout)
    evidence_summary, _legacy = assert_agent_v3_envelope(
        evidence_payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert evidence_summary["submit_repair"] == "repair_result_json"
    assert "use only known_evidence_ids in evidence_refs: ev_known" in evidence_summary["repair_focus"]
    assert "auto_repair_applied" not in evidence_summary
    assert evidence_summary["auto_repair_attempted"] is True
    assert evidence_summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert evidence_summary["core_blocker_preserved"] is True
    assert evidence_summary["core_blocker_kind"] == "evidence_refs_unknown"
    assert evidence_summary["auto_repair_attempted"] is True
    assert evidence_summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert evidence_summary["core_blocker_preserved"] is True
    assert evidence_summary["core_blocker_kind"] == "evidence_refs_unknown"
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-builder"

    assert schema.exit_code == 1
    schema_payload = json.loads(schema.stdout)
    schema_summary, _legacy = assert_agent_v3_envelope(
        schema_payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert schema_summary["submit_repair"] == "repair_result_json"
    assert schema_summary["core_blocker_kind"] == "schema_mismatch"
    assert schema_summary["core_blocker_kind"] == "schema_mismatch"
    assert schema_summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert captured_requests[1].host_dispatch["actual_agent"] == "loopora-builder"

    assert mismatch.exit_code == 1
    mismatch_payload = json.loads(mismatch.stdout)
    mismatch_summary, _legacy = assert_agent_v3_envelope(
        mismatch_payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert mismatch_summary["submit_repair"] == "repair_result_json"
    assert mismatch_summary["submitted_dispatch"]["actual_agent"] == "loopora-gatekeeper"
    assert "auto_repair_applied" not in mismatch_summary
    assert "auto_repair_attempted" not in mismatch_summary
    assert captured_requests[2].host_dispatch["actual_agent"] == "loopora-gatekeeper"

    assert evidence_plain.exit_code == 1
    plain_error = _error_text(evidence_plain)
    assert "auto_repair: submitted result format repaired before submit" in plain_error
    assert "Core still blocked evidence_refs_unknown" in plain_error
    assert plain_error.index("auto_repair:") < plain_error.index("repair_focus:")


def test_cli_agent_submit_schema_error_prints_result_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_schema")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "step_id": "gatekeeper_step",
                        "role": {"name": "GateKeeper", "id": "gatekeeper", "archetype": "gatekeeper"},
                        "role_dispatch": {"target_agent": "loopora-gatekeeper"},
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 3, "gatekeeper_step")),
                        "known_evidence_ids": ["ev_000_00_builder_step", "ev_000_01_inspector_step"],
                        "output_schema": {
                            "type": "object",
                            "properties": {
                                "priority_failures": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["error_code", "summary"],
                                        "properties": {
                                            "error_code": {"type": "string"},
                                            "summary": {"type": "string"},
                                        },
                                    },
                                }
                            },
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file = tmp_path / "bad-result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_schema",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"priority_failures": ["required evidence gap"]},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError("agent-native result does not match output_schema: $.priority_failures[0] expected object, got string")

        def get_run(self, run_id: str):
            assert run_id == "run_schema"
            return {"id": "run_schema", "runs_dir": str(layout.run_dir)}

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
            "run_schema",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    error_text = _error_text(result)
    assert result.exit_code == 1
    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in error_text
    assert f"result_file_to_repair: {result_file}" in error_text
    assert "active_step_id: gatekeeper_step" in error_text
    assert "active_role: GateKeeper" in error_text
    assert "active_target_agent: loopora-gatekeeper" in error_text
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in error_text
    schema_lookup = _assert_labeled_loopora_agent_command(error_text, "schema_lookup", "next")
    assert f"--workdir {workdir.resolve()}" in schema_lookup
    assert "--run-id run_schema" in schema_lookup
    assert "Traceback" not in error_text

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_schema",
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

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert summary["ready"] is False
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["result_file_to_repair"] == str(result_file)
    assert summary["active_step_id"] == "gatekeeper_step"
    assert summary["active_role"] == "GateKeeper"
    assert summary["active_target_agent"] == "loopora-gatekeeper"
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in summary["repair_focus"]
    assert summary["schema_lookup"].endswith("--run-id run_schema --json --entry-source codex_project_skill")


def test_cli_agent_submit_unfilled_template_reports_multiple_schema_repairs(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_unfilled")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    output_schema = {
        "type": "object",
        "properties": {
            "attempted": {"type": "string"},
            "abandoned": {"type": "string"},
            "assumption": {"type": "string"},
            "summary": {"type": "string"},
            "changed_files": {"type": "array", "items": {"type": "string"}},
            "proof_files": {"type": "array", "items": {"type": "string"}},
            "proof_artifacts": {"type": "array", "items": {"type": "object"}},
            "artifact_paths": {"type": "array", "items": {"type": "string"}},
        },
    }
    result_outbox_dir = workdir / ".loopora" / "agent_outbox" / "codex"
    result_file = result_outbox_dir / "run_unfilled__builder_step.result.template.json"
    filled_result_file = result_outbox_dir / "run_unfilled__builder_step.result.json"
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "iter": 1,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 0, "builder_step")),
                        "output_schema": output_schema,
                        "submit_hint": {
                            "result_template_absolute_path": str(result_file),
                            "result_file_absolute_path": str(filled_result_file),
                            "result_outbox_absolute_dir": str(result_outbox_dir),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_unfilled",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {
                    "attempted": None,
                    "abandoned": None,
                    "assumption": None,
                    "summary": None,
                    "changed_files": [None],
                    "proof_files": [None],
                    "proof_artifacts": [None],
                    "artifact_paths": [None],
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError(
                "agent-native result does not match output_schema: "
                "$.attempted expected string, got null; "
                "$.abandoned expected string, got null; "
                "$.assumption expected string, got null; "
                "$.summary expected string, got null; "
                "$.changed_files[0] expected string, got null; "
                "$.proof_files[0] expected string, got null"
            )

        def get_run(self, run_id: str):
            assert run_id == "run_unfilled"
            return {"id": "run_unfilled", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    plain = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_unfilled",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    plain_error = _error_text(plain)
    assert plain.exit_code == 1
    assert f"active_result_template: {result_file}" in plain_error
    assert f"active_result_file_to_write: {filled_result_file}" in plain_error
    assert f"result_outbox_dir: {result_outbox_dir}" in plain_error
    assert "do not overwrite the .result.template.json audit template" in plain_error

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_unfilled",
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

    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["active_step_id"] == "builder_step"
    assert summary["submitted_template_file"] is True
    assert summary["active_result_file_to_write"] == str(filled_result_file)
    assert "save a filled result copy" in summary["next_repair_step"]
    assert "do not overwrite the .result.template.json audit template" in summary["next_repair_step"]
    assert str(filled_result_file) in summary["next_repair_step"]
    repair_focus = summary["repair_focus"]
    assert repair_focus[0] == (
        "replace null placeholders before submit: "
        "$.attempted, $.abandoned, $.assumption, $.summary, $.changed_files[0], $.proof_files[0], "
        "$.proof_artifacts[0], $.artifact_paths[0]"
    )
    assert "$.attempted must be string" in repair_focus
    assert "$.summary must be string" in repair_focus
    assert "$.changed_files[0] must be string" in repair_focus


def test_cli_agent_submit_host_dispatch_errors_report_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_dispatch")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "iter": 1,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 0, "builder_step")),
                        "output_schema": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string"},
                                "changed_files": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_payload = {"summary": "simulated filled copy", "changed_files": []}
    result_file = tmp_path / "wrong-dispatch.result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_dispatch",
                    "iter": 1,
                    "step_id": "builder_step",
                    "step_order": 0,
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": result_payload,
            }
        ),
        encoding="utf-8",
    )
    missing_dispatch_file = tmp_path / "missing-dispatch.result.json"
    missing_dispatch_file.write_text(json.dumps({"result": result_payload}), encoding="utf-8")

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")

        def get_run(self, run_id: str):
            assert run_id == "run_dispatch"
            return {"id": "run_dispatch", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    mismatch = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_dispatch",
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

    assert mismatch.exit_code == 1
    assert _error_text(mismatch) == ""
    mismatch_payload = json.loads(mismatch.stdout)
    mismatch_summary, _legacy = assert_agent_v3_envelope(
        mismatch_payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert mismatch_summary["submit_repair"] == "repair_result_json"
    assert mismatch_summary["active_step_id"] == "builder_step"
    assert mismatch_summary["active_iter"] == 1
    assert mismatch_summary["active_step_order"] == 0
    assert mismatch_summary["submitted_dispatch"]["step_id"] == "builder_step"
    assert mismatch_summary["submitted_dispatch"]["iter"] == 1
    assert mismatch_summary["submitted_dispatch"]["step_order"] == 0
    assert mismatch_summary["submitted_dispatch"]["actual_agent"] == "loopora-gatekeeper"
    assert mismatch_summary["active_target_agent"] == "loopora-builder"
    assert (
        "set loopora_host_dispatch.target_agent and actual_agent to loopora-builder, inline to false, "
        "keep adapter/run_id/iter/step_id/step_order exact, and preserve optional native_trace fields when the host exposed them"
    ) in mismatch_summary["repair_focus"]
    assert "fix loopora_host_dispatch to match the active role dispatch" in mismatch_summary["next_repair_step"]
    assert "loopora-builder" in mismatch_summary["next_repair_step"]

    missing = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_dispatch",
            "--step-id",
            "builder_step",
            "--result-file",
            str(missing_dispatch_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert missing.exit_code == 1
    assert _error_text(missing) == ""
    missing_payload = json.loads(missing.stdout)
    missing_summary, _legacy = assert_agent_v3_envelope(
        missing_payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert missing_summary["submit_repair"] == "repair_result_json"
    assert "use one wrapper JSON object with loopora_host_dispatch and result" in missing_summary["repair_focus"]
    assert "restore loopora_host_dispatch by copying it from the active result template" in missing_summary["next_repair_step"]
