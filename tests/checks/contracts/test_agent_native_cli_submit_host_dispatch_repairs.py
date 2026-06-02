from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    LooporaConflictError,
    Path,
    RunArtifactLayout,
    _error_text,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_cli_agent_submit_host_dispatch_errors_report_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    fixture = write_host_dispatch_repair_fixture(tmp_path)
    result_payload = {"summary": "simulated filled copy", "changed_files": []}
    result_file = write_submit_result_file(
        tmp_path,
        "wrong-dispatch.result.json",
        result=result_payload,
        host_dispatch=host_dispatch_payload(actual_agent="loopora-gatekeeper"),
    )
    missing_dispatch_file = write_submit_result_file(tmp_path, "missing-dispatch.result.json", result=result_payload)

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")

        def get_run(self, run_id: str):
            assert run_id == "run_dispatch"
            return {"id": "run_dispatch", "runs_dir": str(fixture["layout"].run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    mismatch = invoke_host_dispatch_submit(runner, fixture["workdir"], result_file)

    mismatch_summary = submit_repair_summary(mismatch)
    assert_summary_subset(mismatch_summary, active_step_id="builder_step", active_iter=1, active_step_order=0)
    assert_summary_subset(
        mismatch_summary["submitted_dispatch"],
        step_id="builder_step",
        iter=1,
        step_order=0,
        actual_agent="loopora-gatekeeper",
    )
    assert mismatch_summary["active_target_agent"] == "loopora-builder"
    assert (
        "set loopora_host_dispatch.target_agent and actual_agent to loopora-builder, inline to false, "
        "keep adapter/run_id/iter/step_id/step_order exact, and preserve optional native_trace fields when the host exposed them"
    ) in mismatch_summary["repair_focus"]
    assert "fix loopora_host_dispatch to match the active role dispatch" in mismatch_summary["next_repair_step"]
    assert "loopora-builder" in mismatch_summary["next_repair_step"]

    missing = invoke_host_dispatch_submit(runner, fixture["workdir"], missing_dispatch_file)

    missing_summary = submit_repair_summary(missing)
    assert "use one wrapper JSON object with loopora_host_dispatch and result" in missing_summary["repair_focus"]
    assert "restore loopora_host_dispatch by copying it from the active result template" in missing_summary["next_repair_step"]


def write_host_dispatch_repair_fixture(tmp_path: Path) -> dict:
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
                            "properties": {"summary": {"type": "string"}, "changed_files": {"type": "array", "items": {"type": "string"}}},
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"workdir": workdir, "layout": layout}


def host_dispatch_payload(**overrides: object) -> dict:
    payload = {
        "adapter": "codex",
        "run_id": "run_dispatch",
        "iter": 1,
        "step_id": "builder_step",
        "step_order": 0,
        "target_agent": "loopora-builder",
        "actual_agent": "loopora-builder",
        "dispatch_mode": "host_subagent",
        "inline": False,
    }
    payload.update(overrides)
    return payload


def write_submit_result_file(tmp_path: Path, filename: str, *, result: dict, host_dispatch: dict | None = None) -> Path:
    payload = {"result": result}
    if host_dispatch is not None:
        payload["loopora_host_dispatch"] = host_dispatch
    result_file = tmp_path / filename
    result_file.write_text(json.dumps(payload), encoding="utf-8")
    return result_file


def invoke_host_dispatch_submit(runner: CliRunner, workdir: Path, result_file: Path):
    return runner.invoke(
        cli.app,
        [
            "agent", "codex", "submit",
            "--workdir", str(workdir),
            "--run-id", "run_dispatch",
            "--step-id", "builder_step",
            "--result-file", str(result_file),
            "--entry-source", "codex_project_skill",
            "--no-web", "--json",
        ],
    )


def submit_repair_summary(result) -> dict:
    assert result.exit_code == 1
    assert _error_text(result) == ""
    summary, _legacy = assert_agent_v3_envelope(
        json.loads(result.stdout), kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    assert summary["submit_repair"] == "repair_result_json"
    return summary


def assert_summary_subset(payload: dict, **expected: object) -> None:
    assert {key: payload[key] for key in expected} == expected
