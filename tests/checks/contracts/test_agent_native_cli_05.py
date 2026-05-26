from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    RunArtifactLayout,
    WorkflowError,
    _assert_bad_ref_submit_repair_payload,
    _assert_labeled_loopora_agent_command,
    _assert_plain_bad_ref_submit_repair,
    _assert_stale_submit_repair_payload,
    _error_text,
    _invoke_codex_submit,
    _write_agent_submit_repair_fixture,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_submit_repair_json_summarizes_stale_step_and_unknown_evidence(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_agent_submit_repair_fixture(tmp_path)
    workdir = fixture["workdir"]
    layout = fixture["layout"]
    active_template = fixture["active_template"]
    stale_result_file = fixture["stale_result_file"]
    bad_ref_file = fixture["bad_ref_file"]

    class FakeService:
        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            if request.step_id == "builder_step":
                raise LooporaConflictError("submitted step_id does not match the claimed agent-native step")
            raise LooporaError("agent-native evidence_refs_unknown: invented_ev")

        def get_run(self, run_id: str):
            assert run_id == "run_submit_repair"
            return {"id": "run_submit_repair", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    stale = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="builder_step",
        result_file=stale_result_file,
    )

    assert stale.exit_code == 1
    assert _error_text(stale) == ""
    _assert_stale_submit_repair_payload(json.loads(stale.stdout), active_template=active_template)

    bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
    )

    assert bad_ref.exit_code == 1
    assert _error_text(bad_ref) == ""
    _assert_bad_ref_submit_repair_payload(json.loads(bad_ref.stdout))

    plain_bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
        json_output=False,
    )

    plain_error = _error_text(plain_bad_ref)
    assert plain_bad_ref.exit_code == 1
    _assert_plain_bad_ref_submit_repair(plain_error)


def test_cli_agent_submit_invalid_json_prints_result_file_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_bad_json")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "step_id": "builder_step",
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_context_path(0, 0, "builder_step")),
                        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
                        "submit_hint": {
                            "result_template_absolute_path": str(tmp_path / "run_bad_json__builder_step.result.template.json"),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file = tmp_path / "bad-json.result.json"
    result_file.write_text('{"loopora_host_dispatch": ', encoding="utf-8")

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_bad_json"
            return {"id": "run_bad_json", "runs_dir": str(layout.run_dir)}

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
            "run_bad_json",
            "--step-id",
            "builder_step",
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
    assert "active_step_id: builder_step" in error_text
    assert "active_role: Builder" in error_text
    assert "active_target_agent: loopora-builder" in error_text
    assert "fix JSON syntax" in error_text
    schema_lookup = _assert_labeled_loopora_agent_command(error_text, "schema_lookup", "next")
    assert f"--workdir {workdir.resolve()}" in schema_lookup
    assert "--run-id run_bad_json" in schema_lookup
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
            "run_bad_json",
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

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert summary["ready"] is False
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["result_file_to_repair"] == str(result_file)
    assert summary["active_step_id"] == "builder_step"
    assert summary["active_role"] == "Builder"
    assert summary["active_target_agent"] == "loopora-builder"
    assert any("fix JSON syntax" in item for item in summary["repair_focus"])
    assert summary["schema_lookup"].endswith("--run-id run_bad_json --json --entry-source codex_project_skill")

    missing_file = tmp_path / "missing-filled.result.json"
    missing = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_bad_json",
            "--step-id",
            "builder_step",
            "--result-file",
            str(missing_file),
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
    assert missing_summary["result_file_to_repair"] == str(missing_file)
    assert any("create the filled result JSON file at result_file_to_repair" in item for item in missing_summary["repair_focus"])
    assert "create the missing filled result file" in missing_summary["next_repair_step"]
    assert "run_bad_json__builder_step.result.template.json" in missing_summary["next_repair_step"]


def test_cli_agent_submit_reports_workflow_errors_without_traceback(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_test",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "unreachable"},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise WorkflowError("workflow control max_fires_per_run must be between 1 and 20")

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
            "run_corrupt",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    assert "max_fires_per_run" in _error_text(result)
    assert "Traceback" not in _error_text(result)
