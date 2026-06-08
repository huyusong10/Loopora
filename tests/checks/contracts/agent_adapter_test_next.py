from __future__ import annotations

import json


from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_surface import (
    _assert_codex_native_surface_summary,
)


EXPECTED_AGENT_NEXT_KNOWN_EVIDENCE_COUNT = 4


def _assert_agent_next_json_summary(stdout: str) -> None:
    payload = json.loads(stdout)
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_next", summary_key="agent_next_summary", status="active")
    assert "agent_submit_summary" not in summary
    assert summary["handoff_kind"] == "current_step"
    assert summary["run_id"] == "run_next"
    assert summary["run_status"] == "awaiting_agent"
    assert summary["run_url"] == "/runs/run_next"
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    assert summary["next_evidence_focus"] == "Previous GateKeeper rejected the pass because evidence was non-supporting."
    assert summary["next_step_id"] == "inspector_step"
    assert summary["next_target_agent"] == "loopora-inspector"
    assert summary["dispatch_next"] == (
        "invoke loopora-inspector with the next context and step contract paths below; do not perform this role inline"
    )
    assert summary["next_context_path"] == "iterations/iter_000/steps/01__inspector_step/step_instruction_context.json"
    assert summary["next_step_contract_path"] == "iterations/iter_000/steps/01__inspector_step/step_contract.json"
    assert summary["next_result_template"] == ".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json"
    assert summary["next_submit_command"] == "loopora agent codex submit --run-id run_next"
    assert summary["next_role_dispatch_message"] == summary["next_step"]["role_dispatch_message"]
    summary_keys = list(summary)
    assert summary_keys.index("agent_work_panel") < summary_keys.index("agent_surface")
    _assert_agent_work_panel_summary(summary["agent_work_panel"])
    _assert_agent_next_step_json_summary(summary["next_step"])
    _assert_codex_native_surface_summary(summary)


def _assert_agent_next_step_json_summary(next_summary: dict) -> None:
    assert next_summary["step_id"] == "inspector_step"
    assert next_summary["role"] == "Inspector"
    assert next_summary["target_agent"] == "loopora-inspector"
    assert next_summary["target_agent_config"] == ".codex/agents/loopora-inspector.toml"
    assert next_summary["dispatch_next"] == (
        "invoke loopora-inspector with the next context and step contract paths below; do not perform this role inline"
    )
    assert next_summary["native_todo"]["recommended"] is True
    assert next_summary["native_todo"]["not_evidence"] is True
    assert next_summary["native_todo"]["items"] == _expected_agent_next_todo_items()
    assert next_summary["action_policy"] == "read_only, can_block"
    assert next_summary["context_path"] == "iterations/iter_000/steps/01__inspector_step/step_instruction_context.json"
    assert next_summary["step_contract_path"] == "iterations/iter_000/steps/01__inspector_step/step_contract.json"
    assert next_summary["result_template"] == ".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json"
    assert next_summary["result_template_contract"].startswith("Result file must contain one wrapper JSON object")
    assert "replace null placeholders" in next_summary["result_template_fill"]
    assert next_summary["result_outbox_dir"] == ".loopora/agent_outbox/codex"
    assert next_summary["submit_command"] == "loopora agent codex submit --run-id run_next"
    _assert_agent_role_dispatch_message(next_summary["role_dispatch_message"])
    assert next_summary["known_evidence_count"] == EXPECTED_AGENT_NEXT_KNOWN_EVIDENCE_COUNT
    assert next_summary["known_evidence_ids"] == ["ev_builder", "ev_contract"]
    assert next_summary["known_evidence_scope"] == "filtered by evidence_query archetypes=builder limit=12"
    assert next_summary["known_evidence_refs"][0]["id"] == "ev_builder"
    assert next_summary["known_evidence_refs"][0]["gatekeeper_support"] == "non_supporting"
    assert next_summary["known_evidence_refs"][0]["gatekeeper_support_reason"] == "no proof artifact"
    assert next_summary["known_evidence_refs"][0]["artifact_refs"] == [
        {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
    ]
    assert next_summary["known_evidence_refs"][1]["id"] == "ev_contract"
    assert next_summary["known_evidence_refs"][1]["result"] == "blocked"
    assert next_summary["known_evidence_refs"][1]["coverage_target_ids"] == ["done_when.check_001"]
    assert next_summary["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    assert next_summary["coverage_targets"] == [
        {
            "id": "done_when.check_001",
            "kind": "done_when",
            "required": True,
            "text": "The primary user-facing flow works end to end for the target user.",
        },
        {
            "id": "gatekeeper.finish",
            "kind": "gatekeeper",
            "required": True,
            "text": "GateKeeper must cite supporting upstream evidence refs.",
        },
    ]
    assert next_summary["top_coverage_gaps"] == [
        {
            "target_id": "done_when.check_001",
            "status": "weak",
            "text": "Authorization proof is still weak.",
        }
    ]
    repair = next_summary["iteration_repair"]
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["source_role"] == "GateKeeper"
    assert repair["blocking_items"] == [
        "gatekeeper_pass_refs_not_supporting_evidence: a pass must cite upstream evidence that is not blocked, failed, rejected, or errored; produce direct project-owned proof or mark passed=false"
    ]
    assert repair["recommended_next_action"] == "Produce direct project-owned proof before asking GateKeeper to pass again."
    assert repair["evidence_refs"] == ["ev_gatekeeper_block"]
    assert repair["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert next_summary["required_coverage"] == "weak; required checks 1 covered / 1 missing"


def _assert_agent_role_dispatch_message(message: str) -> None:
    assert "Use this exact string as the whole Agent/Task prompt" in message
    assert "prepend `You are running as`" in message
    assert "append `Do the following`" in message
    assert "Invoke the named host-native role agent" in message
    assert "target_agent=loopora-inspector" in message
    assert "context_path=iterations/iter_000/steps/01__inspector_step/step_instruction_context.json" in message
    assert "step_contract_path=iterations/iter_000/steps/01__inspector_step/step_contract.json" in message
    assert "result_template=.loopora/agent_outbox/codex/run_next__inspector_step.result.template.json" in message
    assert "action_policy=read_only, can_block" in message
    assert "coverage_target_ids=done_when.check_001, gatekeeper.finish" in message
    assert "known_evidence_ids=ev_builder, ev_contract" in message
    assert "return one raw wrapper JSON object only" in message
    assert "Main session writes/submits result" in message
    assert "Do not paste full CLI JSON" in message
    assert "full schemas" in message
    assert "large evidence ledgers" in message
    assert "wrapper examples" in message
    assert "no proof artifact" not in message


def _assert_agent_work_panel_summary(panel: dict) -> None:
    assert list(panel) == [
        "state",
        "run_id",
        "task_proven",
        "task_outcome",
        "current_role",
        "current_step_id",
        "next_action",
        "evidence_focus",
        "top_gaps",
        "ask_user",
        "todo_items",
        "run_url",
    ]
    assert panel["state"] == "awaiting_agent"
    assert panel["run_id"] == "run_next"
    assert panel["task_proven"] is False
    assert panel["task_outcome"] == "not_proven_continue_evidence"
    assert panel["current_role"] == "Inspector"
    assert panel["current_step_id"] == "inspector_step"
    assert panel["next_action"] == (
        "invoke loopora-inspector with the next context and step contract paths below; do not perform this role inline"
    )
    assert panel["evidence_focus"] == "done_when.check_001 [weak] Authorization proof is still weak."
    assert panel["todo_items"] == _expected_agent_next_todo_items()
    assert panel["top_gaps"] == [
        {
            "target_id": "done_when.check_001",
            "status": "weak",
            "text": "Authorization proof is still weak.",
        }
    ]
    assert panel["run_url"] == "/runs/run_next"


def _expected_agent_next_todo_items() -> list[str]:
    return [
        "Read top-level summary and the step contract.",
        "Invoke loopora-inspector through the host-native role agent mechanism.",
        "Fill the result template with schema-shaped output and preserve loopora_host_dispatch.",
        "Submit the filled result and read top-level summary before continuing.",
    ]
