from __future__ import annotations

from loopora.agent_adapter_entry_contracts import agent_plan_contract
from loopora.agent_adapter_role_contracts import role_agent_body
from loopora.context_flow import output_contract_prompt
from loopora.residual_risk_prompt_guidance import (
    AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE,
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)
from loopora.service_prompts import ServiceRunPromptMixin


def test_gatekeeper_prompt_guidance_keeps_covered_facts_out_of_residual_risks() -> None:
    plan_contract = agent_plan_contract(
        adapter="claude",
        adapter_label="Claude Code",
        marker_source="claude_project_skill",
    )
    role_body = role_agent_body("gatekeeper")
    step_output_contract = output_contract_prompt("gatekeeper")
    legacy_gatekeeper_prompt = ServiceRunPromptMixin()._verifier_prompt(
        {"goal": "Prove the task.", "checks": [], "constraints": "Use project-owned evidence."},
        tester_output={},
        iter_id=0,
        mode="agent",
    )

    assert AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE in plan_contract
    assert "Future-scope notes are not residual risk" in plan_contract
    for prompt in (role_body, step_output_contract, legacy_gatekeeper_prompt):
        assert GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE in prompt
        assert "Do not put out-of-scope future expansion notes" in prompt
        assert "each item must name an owner, follow-up, or acceptance path" in prompt
        assert "put it in blocking_issues or fail closed instead" in prompt


def test_gatekeeper_role_prompt_fails_closed_on_unreconciled_dynamic_checks() -> None:
    gatekeeper_body = role_agent_body("gatekeeper")
    inspector_body = role_agent_body("inspector")

    assert "GateKeeper fail-closed dynamic-check rule" in gatekeeper_body
    assert "NOT-OK" in gatekeeper_body
    assert "unexpected value" in gatekeeper_body
    assert "proof file is empty, unexpectedly short" in gatekeeper_body
    assert "misordered shell redirection" in gatekeeper_body
    assert "`passed` false" in gatekeeper_body
    assert "name the unresolved failure" in gatekeeper_body
    assert "GateKeeper fail-closed dynamic-check rule" not in inspector_body


def test_gatekeeper_prompts_prefer_supporting_upstream_evidence_before_reruns() -> None:
    step_output_contract = output_contract_prompt("gatekeeper")
    role_body = role_agent_body("gatekeeper")
    legacy_gatekeeper_prompt = ServiceRunPromptMixin()._verifier_prompt(
        {"goal": "Prove the task.", "checks": [], "constraints": "Use project-owned evidence."},
        tester_output={},
        iter_id=0,
        mode="agent",
    )

    for prompt in (role_body, step_output_contract, legacy_gatekeeper_prompt):
        assert GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE in prompt
        assert "inspect known evidence, coverage gaps, handoffs, and cited artifacts before running" in prompt
        assert "decide from those exact evidence_refs without rerunning the same successful proof command" in prompt
        assert "Run a new command or probe only to resolve missing, weak, conflicting, or stale evidence" in prompt

    assert GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE not in role_agent_body("inspector")
