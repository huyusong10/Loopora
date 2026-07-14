from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_compact_envelope, assert_agent_v3_envelope
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
    _assert_agent_native_handoff_surface_plain(output)
    assert (
        f"dispatch_next: invoke {target_agent} with the next context and step contract paths below; "
        "do not perform this role inline"
    ) in output
    assert f"native_dispatch_contract: host-native {target_agent}; nested_provider_cli=not_used" in output
    assert "submit_contract=loopora_host_dispatch + schema-shaped result template" in output
    assert "native_dispatch_mechanism: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output
    assert "native_proof_boundary: native todo/trace may guide host work; Loopora evidence refs" in output


def _assert_agent_native_handoff_surface_plain(output: str) -> None:
    assert "agent surface:" in output
    assert "- capabilities: role_dispatch=host_native" in output
    assert "workspace=current_host_agent_workdir" in output
    assert "proof=loopora_evidence_refs_and_task_verdict" in output
    assert "- activation: explicit_loopora_command_or_cli_only" in output
    assert "- host dispatch: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output
    assert "- accepted native tools: spawn_agent" in output
    assert "- execution: nested provider CLI=not_used" in output
    assert "- submit contract: loopora_host_dispatch + schema-shaped result template" in output
    assert "- packaging:" not in output


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
            "guidance": "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same Agent session to start the next evidence pass from this verdict.",
            "task_verdict_summary": "Audit proof is still missing.",
        },
    }


def _assert_agent_next_plain_work_panel(output: str) -> None:
    assert output.index("agent_work_panel:") < output.index("Loopora run:")
    assert output.index("run_url_status: relative_path_web_not_started") < output.index("Loopora run:")
    assert output.index("run_url_web_start_command:") < output.index("Loopora run:")
    assert "target_agent: loopora-inspector" in output
    assert "role_handoff_status: ready_for_host_dispatch" in output
    assert "role_handoff_owner: current_host_agent" in output
    assert "evidence_focus:" in output
    assert "todo_items:" not in output
    assert "native_todo:" not in output
    assert output.index("technical_handoff:") < output.index("result_template_path:")


def _mkdir(path: Path) -> Path:
    path.mkdir()
    return path


def _write_agent_submit_auto_repair_fixture(tmp_path: Path) -> dict:
    run_id = "run_auto_repair"
    step_id = "builder_step"
    target_agent = "loopora-builder"
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / run_id)
    layout.initialize()
    agent_native_dir = layout.run_dir / "agent_native"
    agent_native_dir.mkdir(parents=True, exist_ok=True)
    result_outbox_dir = workdir / ".loopora" / "agent_outbox" / "codex"
    result_outbox_dir.mkdir(parents=True, exist_ok=True)
    active_template = result_outbox_dir / f"{run_id}__{step_id}.result.template.json"
    host_dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": run_id,
        "iter": 0,
        "step_id": step_id,
        "step_order": 0,
        "target_agent": target_agent,
        "actual_agent": target_agent,
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
                    "agent_step_view": {
                        "adapter": "codex",
                        "run_id": run_id,
                        "iter": 0,
                        "step_id": step_id,
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": target_agent},
                        "known_evidence_ids": ["ev_known"],
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 0, step_id)),
                        "output_schema": {"type": "object", "properties": {"summary": {"type": "string"}}},
                        "submit_hint": {
                            "result_template_absolute_path": str(active_template),
                            "result_file_absolute_path": str(result_outbox_dir / f"{run_id}__{step_id}.result.json"),
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
    '_assert_agent_native_handoff_surface_plain',
    '_assert_agent_next_json_summary',
    '_assert_agent_next_plain_work_panel',
    '_assert_bad_ref_submit_repair_payload',
    '_assert_cli_handoff_contract_paths',
    '_assert_cli_list',
    '_assert_cli_native_dispatch_contract',
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
    'assert_agent_v3_compact_envelope',
    'assert_agent_v3_envelope',
    'cli',
    'json',
]
