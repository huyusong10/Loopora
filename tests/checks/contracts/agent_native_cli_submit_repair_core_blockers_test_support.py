from __future__ import annotations

from typing import Any

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

assert_labeled_loopora_agent_command = _assert_labeled_loopora_agent_command
error_text = _error_text

CORE_BLOCKER_RUN_ID = "run_auto_repair"
CORE_BLOCKER_STEP_ID = "builder_step"
UNKNOWN_EVIDENCE_REFS = ["invented_ev"]
SCHEMA_MISMATCH_SUMMARY_VALUE = 123

SCHEMA_REPAIR_RUN_ID = "run_schema"
SCHEMA_REPAIR_STEP_ID = "gatekeeper_step"
SCHEMA_REPAIR_TARGET_AGENT = "loopora-gatekeeper"


def write_core_blocker_fixture(tmp_path: Path) -> dict:
    return _write_agent_submit_auto_repair_fixture(tmp_path)


def write_core_blocker_result_files(fixture: dict) -> dict[str, Path]:
    evidence_file = fixture["workdir"] / "unknown-evidence.json"
    evidence_file.write_text(
        json.dumps({"summary": "Bad evidence refs.", "evidence_refs": UNKNOWN_EVIDENCE_REFS}),
        encoding="utf-8",
    )
    schema_file = fixture["workdir"] / "schema-mismatch.json"
    schema_file.write_text(json.dumps({"summary": SCHEMA_MISMATCH_SUMMARY_VALUE}), encoding="utf-8")
    mismatch_file = fixture["workdir"] / "dispatch-mismatch.json"
    mismatch_dispatch = dict(fixture["host_dispatch"], actual_agent=SCHEMA_REPAIR_TARGET_AGENT)
    mismatch_file.write_text(
        json.dumps({"loopora_host_dispatch": mismatch_dispatch, "result": {"summary": "Wrong agent."}}),
        encoding="utf-8",
    )
    return {"evidence": evidence_file, "schema": schema_file, "mismatch": mismatch_file}


def install_core_blocker_service(monkeypatch: Any, fixture: dict) -> list[AgentNativeStepSubmitRequest]:
    captured_requests: list[AgentNativeStepSubmitRequest] = []

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == CORE_BLOCKER_RUN_ID
            return {"id": run_id, "runs_dir": str(fixture["layout"].run_dir)}

        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            captured_requests.append(request)
            if request.output.get("evidence_refs") == UNKNOWN_EVIDENCE_REFS:
                raise LooporaError("agent-native evidence_refs_unknown: invented_ev")
            if request.output.get("summary") == SCHEMA_MISMATCH_SUMMARY_VALUE:
                raise LooporaConflictError("agent-native result does not match output_schema: $.summary expected string")
            raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")

    monkeypatch.setattr(cli, "create_service", FakeService)
    return captured_requests


def invoke_core_blocker_submit(fixture: dict, result_file: Path, *, json_output: bool):
    runner = CliRunner()
    return _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id=CORE_BLOCKER_RUN_ID,
        step_id=CORE_BLOCKER_STEP_ID,
        result_file=result_file,
        json_output=json_output,
    )


def submit_repair_summary(result) -> dict:
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    return summary


def write_schema_repair_guidance_fixture(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / SCHEMA_REPAIR_RUN_ID)
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "step_id": SCHEMA_REPAIR_STEP_ID,
                        "role": {"name": "GateKeeper", "id": "gatekeeper", "archetype": "gatekeeper"},
                        "role_dispatch": {"target_agent": SCHEMA_REPAIR_TARGET_AGENT},
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 3, SCHEMA_REPAIR_STEP_ID)),
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
                    "run_id": SCHEMA_REPAIR_RUN_ID,
                    "step_id": SCHEMA_REPAIR_STEP_ID,
                    "target_agent": SCHEMA_REPAIR_TARGET_AGENT,
                    "actual_agent": SCHEMA_REPAIR_TARGET_AGENT,
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"priority_failures": ["required evidence gap"]},
            }
        ),
        encoding="utf-8",
    )
    return {"workdir": workdir, "layout": layout, "result_file": result_file}


def install_schema_repair_guidance_service(monkeypatch: Any, fixture: dict) -> None:
    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError(
                "agent-native result does not match output_schema: $.priority_failures[0] expected object, got string"
            )

        def get_run(self, run_id: str):
            assert run_id == SCHEMA_REPAIR_RUN_ID
            return {"id": SCHEMA_REPAIR_RUN_ID, "runs_dir": str(fixture["layout"].run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)


def invoke_schema_repair_guidance_submit(fixture: dict, *, json_output: bool):
    runner = CliRunner()
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(fixture["workdir"]),
        "--run-id",
        SCHEMA_REPAIR_RUN_ID,
        "--step-id",
        SCHEMA_REPAIR_STEP_ID,
        "--result-file",
        str(fixture["result_file"]),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]
    if json_output:
        args.append("--json")
    return runner.invoke(cli.app, args)
