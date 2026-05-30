from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    AgentNativeStepClaimRequest,
    AgentNativeStepSubmitRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    RunArtifactLayout,
    WorkflowError,
    _assert_agent_next_json_summary,
    _assert_bad_ref_submit_repair_payload,
    _assert_cli_handoff_contract_paths,
    _assert_cli_list,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _assert_labeled_loopora_agent_command,
    _assert_plain_bad_ref_submit_repair,
    _assert_stale_submit_repair_payload,
    _error_text,
    _invoke_codex_submit,
    _write_agent_submit_repair_fixture,
    cli,
    json,
)
from loopora.cli_agent_work_panel import agent_work_panel



def _assert_cli_native_dispatch_contract(output: str, target_agent: str) -> None:
    _assert_codex_native_surface_plain(output)
    assert (
        f"dispatch_next: invoke {target_agent} with the next context and step contract paths below; "
        "do not perform this role inline"
    ) in output
    assert f"native_dispatch_contract: host-native {target_agent}; nested_provider_cli=not_used" in output
    assert "submit_contract=loopora_host_dispatch + schema-shaped result template" in output
    assert "native_dispatch_mechanism: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output
    assert "native_proof_boundary: native todo/trace may guide host work; Loopora evidence refs" in output


def _write_terminal_unproven_run_contract(layout: RunArtifactLayout) -> None:
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep terminal replay honest about evidence.",
                "loop_fit_reasons": ["A later Agent pass can add missing proof."],
                "judgment_tradeoffs": ["Never equate run lifecycle with task proof."],
                "execution_strategy": ["Continue from the missing audit evidence."],
                "local_governance": ["Record the task verdict before another pass."],
                "role_postures": [
                    {
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Report unproven evidence as unproven.",
                    }
                ],
                "success_surface": ["Audit evidence proves the user-visible flow."],
                "fake_done_states": ["A succeeded run with missing evidence is not done."],
                "evidence_preferences": ["Use project-owned checks and artifact paths."],
                "residual_risk": "No residual risk may hide missing audit proof.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _terminal_unproven_loop_payload(layout: RunArtifactLayout) -> dict:
    return {
        "execution_plane": "agent_native",
        "run": {
            "id": "run_terminal_loop",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(layout.run_dir),
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "gatekeeper",
                "summary": "Audit proof is still missing.",
            },
        },
        "run_path": "/runs/run_terminal_loop",
        "started_new_run": False,
        "complete": True,
        "task_next_action": {
            "kind": "continue_evidence",
            "next_loop_command": "/loopora-run",
            "guidance": "Run lifecycle is complete, but the task is not proven.",
            "task_verdict_summary": "Audit proof is still missing.",
        },
    }


def _assert_agent_next_plain_work_panel(output: str) -> None:
    assert output.index("agent_work_panel:") < output.index("Loopora run:")
    assert "todo_items:" in output
    assert "- Invoke loopora-inspector through the host-native role agent mechanism." in output
    assert "native_todo: Create or update the host's official todo/progress list when available" in output
    assert "do not cite todo completion as Loopora evidence" in output
    assert output.index("technical_handoff:") < output.index("result_template_path:")


def _mkdir(path: Path) -> Path:
    path.mkdir()
    return path


def _write_agent_submit_auto_repair_fixture(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_auto_repair")
    layout.initialize()
    agent_native_dir = layout.run_dir / "agent_native"
    agent_native_dir.mkdir(parents=True, exist_ok=True)
    result_outbox_dir = workdir / ".loopora" / "agent_outbox" / "codex"
    result_outbox_dir.mkdir(parents=True, exist_ok=True)
    active_template = result_outbox_dir / "run_auto_repair__builder_step.result.template.json"
    host_dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": "run_auto_repair",
        "iter": 0,
        "step_id": "builder_step",
        "step_order": 0,
        "target_agent": "loopora-builder",
        "actual_agent": "loopora-builder",
        "dispatch_mode": "host_subagent",
        "inline": False,
    }
    active_template.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": host_dispatch,
                "result": {"summary": None},
            }
        ),
        encoding="utf-8",
    )
    (agent_native_dir / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "adapter": "codex",
                        "run_id": "run_auto_repair",
                        "iter": 0,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "known_evidence_ids": ["ev_known"],
                        "context_absolute_path": str(layout.step_context_path(0, 0, "builder_step")),
                        "output_schema": {"type": "object", "properties": {"summary": {"type": "string"}}},
                        "submit_hint": {
                            "result_template_absolute_path": str(active_template),
                            "result_file_absolute_path": str(result_outbox_dir / "run_auto_repair__builder_step.result.json"),
                            "result_outbox_absolute_dir": str(result_outbox_dir),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {
        "workdir": workdir,
        "layout": layout,
        "active_template": active_template,
        "host_dispatch": host_dispatch,
    }


def _agent_submit_auto_repair_success_payload(fixture: dict, request: AgentNativeStepSubmitRequest) -> dict:
    return {
        "run": {
            "id": request.run_id,
            "status": "awaiting_agent",
            "run_status": "awaiting_agent",
            "runs_dir": str(fixture["layout"].run_dir),
            "task_verdict": {"status": "not_evaluated", "summary": "Task still needs GateKeeper review."},
        },
        "run_path": f"/runs/{request.run_id}",
        "complete": False,
        "submitted_step": {
            "step_id": request.step_id,
            "status": "completed",
            "summary": request.output.get("summary", ""),
            "evidence_refs": [],
            "blocking_items": [],
        },
        "next_step": {
            "step_id": "gatekeeper_step",
            "role": {"name": "GateKeeper"},
            "role_dispatch": {"target_agent": "loopora-gatekeeper"},
            "submit_hint": {"command": f"loopora agent codex submit --run-id {request.run_id}"},
        },
    }

__all__ = [
    'AgentNativeStepClaimRequest',
    'AgentNativeStepSubmitRequest',
    'CliRunner',
    'LooporaConflictError',
    'LooporaError',
    'Path',
    'RunArtifactLayout',
    'WorkflowError',
    '_agent_submit_auto_repair_success_payload',
    '_assert_agent_next_json_summary',
    '_assert_agent_next_plain_work_panel',
    '_assert_bad_ref_submit_repair_payload',
    '_assert_cli_handoff_contract_paths',
    '_assert_cli_list',
    '_assert_cli_native_dispatch_contract',
    '_assert_codex_native_surface_plain',
    '_assert_codex_native_surface_summary',
    '_assert_labeled_loopora_agent_command',
    '_assert_plain_bad_ref_submit_repair',
    '_assert_stale_submit_repair_payload',
    '_error_text',
    '_invoke_codex_submit',
    '_mkdir',
    '_terminal_unproven_loop_payload',
    '_write_agent_submit_auto_repair_fixture',
    '_write_agent_submit_repair_fixture',
    '_write_terminal_unproven_run_contract',
    'agent_work_panel',
    'assert_agent_v3_envelope',
    'cli',
    'json',
]
