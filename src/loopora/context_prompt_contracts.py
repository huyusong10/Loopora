from __future__ import annotations

import json

from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)
from loopora.system_prompt_assets import render_system_prompt_asset


_SYSTEM_PREFIX_ASSETS = {
    "builder": "runtime/system-prefix-builder.md",
    "inspector": "runtime/system-prefix-inspector.md",
    "gatekeeper": "runtime/system-prefix-gatekeeper.md",
    "custom": "runtime/system-prefix-custom.md",
}
_OUTPUT_CONTRACT_ASSETS = {
    "builder": "runtime/output-contract-builder.md",
    "inspector": "runtime/output-contract-inspector.md",
    "gatekeeper": "runtime/output-contract-gatekeeper.md",
    "custom": "runtime/output-contract-custom.md",
}


def system_prompt_prefix(archetype: str) -> str:
    return render_system_prompt_asset(
        _SYSTEM_PREFIX_ASSETS.get(archetype, "runtime/system-prefix-guide.md"),
        {
            "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
            "INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE": INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
        },
    )


def output_contract_prompt(archetype: str) -> str:
    return render_system_prompt_asset(
        _OUTPUT_CONTRACT_ASSETS.get(archetype, "runtime/output-contract-guide.md"),
        {
            "GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE": GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
            "GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE": GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
        },
    )


def render_run_contract_section(contract: dict, compiled_spec: dict) -> str:
    constraints = contract.get("constraints") or "No explicit constraints were provided."
    success_surface = json.dumps(contract.get("success_surface") or [], ensure_ascii=False, indent=2)
    fake_done_states = json.dumps(contract.get("fake_done_states") or [], ensure_ascii=False, indent=2)
    evidence_preferences = json.dumps(contract.get("evidence_preferences") or [], ensure_ascii=False, indent=2)
    coverage_targets = json.dumps(contract.get("coverage_targets") or [], ensure_ascii=False, indent=2)
    collaboration_summary = str(
        contract.get("collaboration_summary") or "No explicit bundle collaboration summary was provided."
    ).strip()
    strategy_collaboration_intent = str(
        contract.get("strategy_collaboration_intent")
        or "No explicit strategy collaboration intent was provided."
    ).strip()
    loop_fit_reasons = json.dumps(contract.get("loop_fit_reasons") or [], ensure_ascii=False, indent=2)
    judgment_tradeoffs = json.dumps(contract.get("judgment_tradeoffs") or [], ensure_ascii=False, indent=2)
    execution_strategy = json.dumps(contract.get("execution_strategy") or [], ensure_ascii=False, indent=2)
    local_governance = json.dumps(contract.get("local_governance") or [], ensure_ascii=False, indent=2)
    role_postures = json.dumps(contract.get("role_postures") or [], ensure_ascii=False, indent=2)
    residual_risk = str(contract.get("residual_risk") or "No explicit residual-risk stance was provided.").strip()
    return (
        "Run contract summary:\n"
        f"- Completion mode: {contract.get('completion_mode')}\n"
        f"- Bundle collaboration summary: {collaboration_summary}\n"
        f"- Loopora fit: {loop_fit_reasons}\n"
        f"- Judgment tradeoffs: {judgment_tradeoffs}\n"
        f"- Execution strategy: {execution_strategy}\n"
        f"- Local governance: {local_governance}\n"
        f"- Role postures: {role_postures}\n"
        f"- Strategy preset: {contract.get('strategy_preset')}\n"
        f"- Strategy collaboration intent: {strategy_collaboration_intent}\n"
        f"- Check mode: {contract.get('check_mode')}\n"
        f"- Check count: {contract.get('check_count')}\n\n"
        f"Goal:\n{contract.get('goal', '').strip()}\n\n"
        f"Checks:\n{json.dumps(compiled_spec.get('checks', []), ensure_ascii=False, indent=2)}\n\n"
        f"Constraints:\n{constraints}\n\n"
        f"Coverage targets:\n{coverage_targets}\n\n"
        f"Success surface:\n{success_surface}\n\n"
        f"Fake done states:\n{fake_done_states}\n\n"
        f"Evidence preferences:\n{evidence_preferences}\n\n"
        f"Residual risk:\n{residual_risk}"
    )


def render_role_note_section(role_note: str) -> str:
    if not str(role_note or "").strip():
        return ""
    return f"Role notes for the current role:\n{str(role_note).strip()}"


def _combine_role_guidance(spec_role_note: str, role_posture: str) -> str:
    parts: list[str] = []
    if str(role_posture or "").strip():
        parts.append(f"Role definition posture:\n{str(role_posture).strip()}")
    if str(spec_role_note or "").strip():
        parts.append(f"Spec role notes:\n{str(spec_role_note).strip()}")
    return "\n\n".join(parts).strip()
