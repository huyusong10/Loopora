from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.run_artifacts import RunArtifactLayout
from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_surface import (
    _assert_codex_native_surface_summary,
)


def _write_agent_submit_repair_fixture(tmp_path: Path) -> dict[str, Path | RunArtifactLayout]:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_submit_repair")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    active_template = workdir / ".loopora" / "agent_outbox" / "codex" / "run_submit_repair__contract_inspection_step.result.template.json"
    active_template.parent.mkdir(parents=True, exist_ok=True)
    active_template.write_text("{}", encoding="utf-8")
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps({"active_step": {"agent_step_view": _agent_submit_repair_active_step_view(layout, active_template)}}, ensure_ascii=False),
        encoding="utf-8",
    )
    stale_result_file = tmp_path / "builder-stale.result.json"
    stale_result_file.write_text(json.dumps(_stale_builder_result_wrapper()), encoding="utf-8")
    bad_ref_file = tmp_path / "inspector-bad-ref.result.json"
    bad_ref_file.write_text(json.dumps(_bad_ref_inspector_result_wrapper()), encoding="utf-8")
    return {
        "workdir": workdir,
        "layout": layout,
        "active_template": active_template,
        "stale_result_file": stale_result_file,
        "bad_ref_file": bad_ref_file,
    }

def _agent_submit_repair_active_step_view(layout: RunArtifactLayout, active_template: Path) -> dict:
    return {
        "iter": 0,
        "step_id": "contract_inspection_step",
        "step_order": 1,
        "role": {"name": "Contract Inspector", "id": "contract_inspector", "archetype": "inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "context_absolute_path": str(layout.step_instruction_context_path(0, 1, "contract_inspection_step")),
        "known_evidence_ids": ["ev_000_00_builder_step"],
        "known_evidence_refs": [
            {
                "id": "ev_000_00_builder_step",
                "step_id": "builder_step",
                "role_name": "Focused Builder",
                "result": "completed",
                "claim": "Builder proof exists but is weak for this repair fixture.",
                "gatekeeper_support": "non_supporting",
                "gatekeeper_support_reason": "no proof artifact",
                "coverage_target_ids": ["done_when.check_001"],
            }
        ],
        "judgment_contract": {
            "coverage_targets": [
                {"id": "done_when.check_001", "text": "Vendor billing callback flow works."},
                {"id": "done_when.check_002", "text": "Failed callbacks are replayable."},
            ]
        },
        "submit_hint": {"result_template_absolute_path": str(active_template)},
    }

def _stale_builder_result_wrapper() -> dict:
    return {
        "loopora_host_dispatch": {
            "adapter": "codex",
            "run_id": "run_submit_repair",
            "iter": 0,
            "step_id": "builder_step",
            "step_order": 0,
            "target_agent": "loopora-builder",
            "actual_agent": "loopora-builder",
            "dispatch_mode": "host_subagent",
            "inline": False,
        },
        "result": {"summary": "stale builder file"},
    }

def _bad_ref_inspector_result_wrapper() -> dict:
    return {
        "loopora_host_dispatch": {
            "adapter": "codex",
            "run_id": "run_submit_repair",
            "step_id": "contract_inspection_step",
            "target_agent": "loopora-inspector",
            "actual_agent": "loopora-inspector",
            "dispatch_mode": "host_subagent",
            "inline": False,
        },
        "result": {
            "coverage_results": [
                {
                    "target_id": "done_when.check_001",
                    "status": "covered",
                    "evidence_refs": ["invented_ev"],
                    "note": "Invented ref for repair UX.",
                }
            ]
        },
    }

def _invoke_codex_submit(runner: CliRunner, workdir: Path, **options):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(workdir),
        "--run-id",
        str(options["run_id"]),
        "--step-id",
        str(options["step_id"]),
        "--result-file",
        str(options["result_file"]),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]
    if options.get("json_output", True):
        args.append("--json")
    return runner.invoke(cli.app, args)

def _assert_stale_submit_repair_payload(payload: dict, *, active_template: Path) -> None:
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    _assert_codex_native_surface_summary(summary)
    assert summary["active_step_id"] == "contract_inspection_step"
    assert summary["active_iter"] == 0
    assert summary["active_step_order"] == 1
    assert summary["active_result_template"] == str(active_template)
    assert summary["submitted_dispatch"]["step_id"] == "builder_step"
    assert summary["submitted_dispatch"]["iter"] == 0
    assert summary["submitted_dispatch"]["step_order"] == 0
    assert "discard the stale result file" in summary["next_repair_step"]
    assert "submitted file is for builder_step (iter 0, step_order 0)" in summary["next_repair_step"]
    assert "active step is contract_inspection_step (iter 0, step_order 1)" in summary["next_repair_step"]
    assert "contract_inspection_step" in summary["next_repair_step"]
    assert "loopora agent codex next" in summary["schema_lookup"]
    assert summary["active_known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support_reason"] == "no proof artifact"

def _assert_bad_ref_submit_repair_payload(payload: dict) -> None:
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit_repair", summary_key="agent_submit_repair_summary", status="blocked"
    )
    _assert_codex_native_surface_summary(summary)
    assert summary["active_known_evidence_ids"] == ["ev_000_00_builder_step"]
    assert summary["active_known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"
    assert summary["active_known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert "replace invented evidence_refs" in summary["next_repair_step"]
    assert "ev_000_00_builder_step" in summary["next_repair_step"]
    assert "use only known_evidence_ids in evidence_refs: ev_000_00_builder_step" in summary["repair_focus"]

def _assert_plain_bad_ref_submit_repair(error_text: str) -> None:
    assert "active_known_evidence_ids:" in error_text
    assert "- ev_000_00_builder_step" in error_text
    assert "active_known_evidence_refs:" in error_text
    assert "- ev_000_00_builder_step result=completed support=non_supporting reason=no proof artifact" in error_text
    assert "claim: Builder proof exists but is weak for this repair fixture." in error_text
    assert "coverage_targets: done_when.check_001" in error_text
    assert "active_coverage_target_ids:" in error_text
    assert "- done_when.check_001" in error_text
    assert "- done_when.check_002" in error_text
