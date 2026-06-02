from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.db import LooporaRepository
from loopora.executor import FakeCodexExecutor
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaService
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.service_agent_native import AgentNativeStepSubmitRequest
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.settings import AppSettings


pytestmark = pytest.mark.real_agent


def _write_auto_repair_state(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_auto_repair_probe")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    outbox = workdir / ".loopora" / "agent_outbox" / "codex"
    outbox.mkdir(parents=True, exist_ok=True)
    template = outbox / "run_auto_repair_probe__builder_step.result.template.json"
    dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": "run_auto_repair_probe",
        "iter": 0,
        "step_id": "builder_step",
        "step_order": 0,
        "target_agent": "loopora-builder",
        "actual_agent": "loopora-builder",
        "dispatch_mode": "host_subagent",
        "inline": False,
    }
    template.write_text(json.dumps({"loopora_host_dispatch": dispatch, "result": {"summary": None}}), encoding="utf-8")
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "adapter": "codex",
                        "run_id": "run_auto_repair_probe",
                        "iter": 0,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {
                            "required": True,
                            "target_agent": "loopora-builder",
                            "inline_allowed": False,
                            "accepted_dispatch_modes": ["host_subagent"],
                        },
                        "known_evidence_ids": ["ev_known"],
                        "output_schema": {
                            "type": "object",
                            "required": ["summary"],
                            "properties": {
                                "summary": {"type": "string"},
                                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                        "action_policy": {"workspace": "workspace_write", "can_block": True, "can_finish_run": False},
                        "required_coverage": {"targets": [{"id": "check_1"}]},
                        "judgment_contract": {"summary": "Probe submit auto-repair without relaxing Core blockers."},
                        "submit_hint": {
                            "result_template_absolute_path": str(template),
                            "result_file_absolute_path": str(outbox / "run_auto_repair_probe__builder_step.result.json"),
                            "result_outbox_absolute_dir": str(outbox),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {"workdir": workdir, "layout": layout, "template": template, "dispatch": dispatch}


def _invoke_submit(runner: CliRunner, fixture: dict, result_file: Path, *, json_output: bool = False):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(fixture["workdir"]),
        "--run-id",
        "run_auto_repair_probe",
        "--step-id",
        "builder_step",
        "--result-file",
        str(result_file),
    ]
    if json_output:
        args.append("--json")
    return runner.invoke(cli.app, args)


def _write_phase_report(workdir: Path, outputs: list[str]) -> Path:
    events = []
    for source_text in outputs:
        events.extend(
            {"source": "cli_stdout", "line": line.strip()}
            for line in source_text.splitlines()
            if "auto_repair" in line.lower() or "auto repair" in line.lower()
        )
    report = {
        "probe": "submit-auto-repair",
        "phase_statuses": {
            "wrapper_repair_observed": {"ok": any("wrapped_schema_result" in item["line"] for item in events)},
            "template_path_repair_observed": {"ok": any("accepted_filled_result_template_path" in item["line"] for item in events)},
            "core_blocker_preserved": {"ok": any("Core still blocked" in item["line"] for item in events)},
        },
        "diagnostics": {
            "experience_health": {
                "auto_repair_events": events,
                "experience_notes": ["auto_repair_is_format_recovery_not_task_proof"],
            }
        },
    }
    report_path = workdir / ".loopora" / "real-probes" / "submit-auto-repair-phase-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def _create_real_core_submit_fixture(tmp_path: Path, case_id: str) -> dict:
    case_dir = tmp_path / case_id
    workdir = case_dir / "project"
    workdir.mkdir(parents=True)
    service = LooporaService(
        repository=LooporaRepository(case_dir / "app.db"),
        settings=AppSettings(max_concurrent_runs=1, polling_interval_seconds=0.1, stop_grace_period_seconds=0.5),
        executor_factory=FakeCodexExecutor,
    )
    bundle_file = case_dir / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    active_step_view = state["active_step"]["agent_step_view"]
    output_schema = active_step_view["output_schema"]
    output_schema.setdefault("properties", {})["evidence_refs"] = {"type": "array", "items": {"type": "string"}}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    role_dispatch = step.get("role_dispatch") if isinstance(step.get("role_dispatch"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "")
    dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": str(step["run_id"]),
        "iter": int(step.get("iter") or 0),
        "step_id": str(step["step_id"]),
        "step_order": int(step.get("step_order") or 0),
        "target_agent": target_agent,
        "actual_agent": target_agent,
        "dispatch_mode": "host_subagent",
        "inline": False,
        "attestation": "Real Core auto-repair probe uses the host wrapper path without relaxing submit validation.",
    }
    return {
        "service": service,
        "workdir": workdir,
        "layout": layout,
        "run_id": str(step["run_id"]),
        "step_id": str(step["step_id"]),
        "step": step,
        "template": Path(step["submit_hint"]["result_template_absolute_path"]),
        "dispatch": dispatch,
    }


def _real_core_builder_output(*, summary: object = "real Core submit output") -> dict:
    return {
        "attempted": "Submitted through the real LooporaService agent-native path.",
        "abandoned": "",
        "assumption": "The probe is only validating submit wrapper repair and Core blocker preservation.",
        "summary": summary,
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }


def _write_json_result(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _invoke_real_core_submit(runner: CliRunner, fixture: dict, result_file: Path, *, json_output: bool = False):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(fixture["workdir"]),
        "--run-id",
        str(fixture["run_id"]),
        "--step-id",
        str(fixture["step_id"]),
        "--result-file",
        str(result_file),
    ]
    if json_output:
        args.append("--json")
    return runner.invoke(cli.app, args)


def _commit_step_then_restore_claimed_state(fixture: dict) -> None:
    state_path = fixture["layout"].run_dir / "agent_native" / "state.json"
    stale_claimed_state = json.loads(state_path.read_text(encoding="utf-8"))
    fixture["service"].submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=fixture["workdir"],
            run_id=fixture["run_id"],
            step_id=fixture["step_id"],
            output=_real_core_builder_output(),
            host_dispatch=fixture["dispatch"],
            entry_source="codex_project_skill",
        )
    )
    state_path.write_text(json.dumps(stale_claimed_state, ensure_ascii=False, indent=2), encoding="utf-8")


def _cli_output(result) -> str:
    return str(result.stdout or result.output or result.exception or "")


def test_submit_auto_repair_wrapper_probe_records_format_repair_and_preserved_blockers(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_auto_repair_state(tmp_path)
    runner = CliRunner()
    captured: list[AgentNativeStepSubmitRequest] = []

    class ProbeService:
        def get_run(self, run_id: str):
            assert run_id == "run_auto_repair_probe"
            return {"id": run_id, "status": "awaiting_agent", "runs_dir": str(fixture["layout"].run_dir)}

        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            captured.append(request)
            summary = request.output.get("summary")
            if summary == "unknown evidence":
                raise LooporaError("agent-native evidence_refs_unknown: ev_missing")
            if summary == 123:
                raise LooporaConflictError("agent-native result does not match output_schema: $.summary expected string")
            if summary == "stale":
                raise LooporaConflictError(
                    "agent-native step was already submitted; rerun agent next --json if the run advanced or this result file is stale"
                )
            if request.host_dispatch.get("actual_agent") == "loopora-gatekeeper":
                raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")
            if request.host_dispatch.get("inline") is True:
                raise LooporaConflictError("agent-native submit cannot claim inline role execution for this step")
            return {
                "run": {"id": request.run_id, "status": "awaiting_agent", "run_status": "awaiting_agent"},
                "run_path": f"/runs/{request.run_id}",
                "complete": False,
                "submitted_step": {"step_id": request.step_id, "status": "completed", "evidence_refs": []},
            }

    monkeypatch.setattr(cli, "create_service", ProbeService)
    direct = fixture["workdir"] / "direct.json"
    direct.write_text(json.dumps({"summary": "ok"}), encoding="utf-8")
    result_only = fixture["workdir"] / "result-only.json"
    result_only.write_text(json.dumps({"result": {"summary": "ok"}}), encoding="utf-8")
    fixture["template"].write_text(
        json.dumps({"loopora_host_dispatch": fixture["dispatch"], "result": {"summary": "ok"}}),
        encoding="utf-8",
    )
    unknown = fixture["workdir"] / "unknown.json"
    unknown.write_text(json.dumps({"summary": "unknown evidence", "evidence_refs": ["ev_missing"]}), encoding="utf-8")
    schema = fixture["workdir"] / "schema.json"
    schema.write_text(json.dumps({"summary": 123}), encoding="utf-8")
    stale = fixture["workdir"] / "stale.json"
    stale.write_text(json.dumps({"summary": "stale"}), encoding="utf-8")
    mismatch = fixture["workdir"] / "mismatch.json"
    mismatch.write_text(
        json.dumps({"loopora_host_dispatch": dict(fixture["dispatch"], actual_agent="loopora-gatekeeper"), "result": {"summary": "ok"}}),
        encoding="utf-8",
    )
    inline = fixture["workdir"] / "inline.json"
    inline.write_text(
        json.dumps({"loopora_host_dispatch": dict(fixture["dispatch"], inline=True), "result": {"summary": "ok"}}),
        encoding="utf-8",
    )

    repaired_wrapper = _invoke_submit(runner, fixture, direct, json_output=True)
    repaired_result_only = _invoke_submit(runner, fixture, result_only, json_output=True)
    repaired_template_path = _invoke_submit(runner, fixture, fixture["template"])
    unknown_blocked = _invoke_submit(runner, fixture, unknown)
    schema_blocked = _invoke_submit(runner, fixture, schema, json_output=True)
    stale_blocked = _invoke_submit(runner, fixture, stale)
    mismatch_blocked = _invoke_submit(runner, fixture, mismatch, json_output=True)
    inline_blocked = _invoke_submit(runner, fixture, inline, json_output=True)

    assert repaired_wrapper.exit_code == 0, repaired_wrapper.stdout
    assert repaired_result_only.exit_code == 0, repaired_result_only.stdout
    assert repaired_template_path.exit_code == 0, repaired_template_path.stdout
    assert "accepted_filled_result_template_path_as_result_file" in _cli_output(repaired_template_path)
    assert unknown_blocked.exit_code == 1
    assert "Core still blocked evidence_refs_unknown" in _cli_output(unknown_blocked)
    assert stale_blocked.exit_code == 1
    assert "Core still blocked stale_step" in _cli_output(stale_blocked)
    assert json.loads(_cli_output(schema_blocked))["summary"]["core_blocker_kind"] == "schema_mismatch"
    assert "auto_repair_attempted" not in json.loads(_cli_output(mismatch_blocked))["summary"]
    assert "auto_repair_attempted" not in json.loads(_cli_output(inline_blocked))["summary"]
    assert captured[0].host_dispatch["actual_agent"] == "loopora-builder"
    assert captured[3].output["evidence_refs"] == ["ev_missing"]

    report_path = _write_phase_report(
        fixture["workdir"],
        [_cli_output(repaired_template_path), _cli_output(unknown_blocked), _cli_output(stale_blocked)],
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    health = report["diagnostics"]["experience_health"]
    assert report["phase_statuses"]["wrapper_repair_observed"]["ok"] is True
    assert report["phase_statuses"]["template_path_repair_observed"]["ok"] is True
    assert report["phase_statuses"]["core_blocker_preserved"]["ok"] is True
    assert any("Core still blocked evidence_refs_unknown" in item["line"] for item in health["auto_repair_events"])


def test_submit_auto_repair_real_core_probe_preserves_validation_blockers(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()

    def invoke_case(result_file: Path, fixture: dict, *, json_output: bool = False):
        monkeypatch.setattr(cli, "create_service", lambda: fixture["service"])
        return _invoke_real_core_submit(runner, fixture, result_file, json_output=json_output)

    bare_fixture = _create_real_core_submit_fixture(tmp_path, "bare-wrapper")
    bare_result = _write_json_result(bare_fixture["workdir"] / "bare-result.json", _real_core_builder_output())
    bare_repaired = invoke_case(bare_result, bare_fixture, json_output=True)

    result_only_fixture = _create_real_core_submit_fixture(tmp_path, "result-only")
    result_only = _write_json_result(result_only_fixture["workdir"] / "result-only.json", {"result": _real_core_builder_output()})
    result_only_repaired = invoke_case(result_only, result_only_fixture, json_output=True)

    template_fixture = _create_real_core_submit_fixture(tmp_path, "template-path")
    _write_json_result(
        template_fixture["template"],
        {"loopora_host_dispatch": template_fixture["dispatch"], "result": _real_core_builder_output()},
    )
    template_repaired = invoke_case(template_fixture["template"], template_fixture)

    unknown_fixture = _create_real_core_submit_fixture(tmp_path, "unknown-evidence")
    unknown_output = {**_real_core_builder_output(summary="unknown evidence"), "evidence_refs": ["ev_missing"]}
    unknown = _write_json_result(unknown_fixture["workdir"] / "unknown.json", unknown_output)
    unknown_blocked = invoke_case(unknown, unknown_fixture)

    schema_fixture = _create_real_core_submit_fixture(tmp_path, "schema-mismatch")
    schema = _write_json_result(schema_fixture["workdir"] / "schema.json", _real_core_builder_output(summary=123))
    schema_blocked = invoke_case(schema, schema_fixture, json_output=True)

    stale_fixture = _create_real_core_submit_fixture(tmp_path, "stale-step")
    _commit_step_then_restore_claimed_state(stale_fixture)
    stale = _write_json_result(stale_fixture["workdir"] / "stale.json", _real_core_builder_output())
    stale_blocked = invoke_case(stale, stale_fixture)

    mismatch_fixture = _create_real_core_submit_fixture(tmp_path, "dispatch-mismatch")
    mismatch = _write_json_result(
        mismatch_fixture["workdir"] / "mismatch.json",
        {
            "loopora_host_dispatch": dict(mismatch_fixture["dispatch"], actual_agent="loopora-gatekeeper"),
            "result": _real_core_builder_output(),
        },
    )
    mismatch_blocked = invoke_case(mismatch, mismatch_fixture, json_output=True)

    inline_fixture = _create_real_core_submit_fixture(tmp_path, "inline-forbidden")
    inline = _write_json_result(
        inline_fixture["workdir"] / "inline.json",
        {
            "loopora_host_dispatch": dict(inline_fixture["dispatch"], inline=True),
            "result": _real_core_builder_output(),
        },
    )
    inline_blocked = invoke_case(inline, inline_fixture, json_output=True)

    assert bare_repaired.exit_code == 0, _cli_output(bare_repaired)
    assert result_only_repaired.exit_code == 0, _cli_output(result_only_repaired)
    assert template_repaired.exit_code == 0, _cli_output(template_repaired)
    assert "accepted_filled_result_template_path_as_result_file" in _cli_output(template_repaired)
    assert unknown_blocked.exit_code == 1
    assert "Core still blocked evidence_refs_unknown" in _cli_output(unknown_blocked)
    assert schema_blocked.exit_code == 1
    assert json.loads(_cli_output(schema_blocked))["summary"]["core_blocker_kind"] == "schema_mismatch"
    assert stale_blocked.exit_code == 1
    assert "Core still blocked stale_step" in _cli_output(stale_blocked)
    assert mismatch_blocked.exit_code == 1
    assert "auto_repair_attempted" not in json.loads(_cli_output(mismatch_blocked))["summary"]
    assert inline_blocked.exit_code == 1
    assert "auto_repair_attempted" not in json.loads(_cli_output(inline_blocked))["summary"]

    report_path = _write_phase_report(
        unknown_fixture["workdir"],
        [_cli_output(bare_repaired), _cli_output(template_repaired), _cli_output(unknown_blocked), _cli_output(stale_blocked)],
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    health = report["diagnostics"]["experience_health"]
    assert report["phase_statuses"]["wrapper_repair_observed"]["ok"] is True
    assert report["phase_statuses"]["template_path_repair_observed"]["ok"] is True
    assert report["phase_statuses"]["core_blocker_preserved"]["ok"] is True
    assert any("Core still blocked evidence_refs_unknown" in item["line"] for item in health["auto_repair_events"])
