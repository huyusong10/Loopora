from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_agent_native import AgentNativeStepSubmitRequest
from loopora.service_types import LooporaConflictError, LooporaError


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
                    "capsule": {
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


def _cli_output(result) -> str:
    return str(result.stdout or result.output or result.exception or "")


def test_submit_auto_repair_probe_records_format_repair_and_preserved_core_blockers(monkeypatch, tmp_path: Path) -> None:
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
