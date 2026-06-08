from __future__ import annotations

from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)
from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset

_ROLE_DESCRIPTION_ASSETS = {
    "builder": "agent_native/role-description-builder.md",
    "inspector": "agent_native/role-description-inspector.md",
    "gatekeeper": "agent_native/role-description-gatekeeper.md",
    "guide": "agent_native/role-description-guide.md",
    "orchestrator": "agent_native/role-description-orchestrator.md",
}


def role_agent_description(role: str) -> str:
    asset_ref = _ROLE_DESCRIPTION_ASSETS.get(role, "agent_native/role-description-generic.md")
    return load_system_prompt_asset(asset_ref).strip()


def role_agent_body(role: str) -> str:
    if role == "orchestrator":
        return render_system_prompt_asset(
            "agent_native/role-agent-orchestrator.md",
            {"PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE},
        )
    label = role.capitalize() if role != "gatekeeper" else "GateKeeper"
    gatekeeper_upstream_evidence_guidance = _gatekeeper_upstream_evidence_guidance(role)
    gatekeeper_dynamic_check_guidance = _gatekeeper_dynamic_check_guidance(role)
    inspector_dynamic_check_guidance = _inspector_dynamic_check_guidance(role)
    return render_system_prompt_asset(
        "agent_native/role-agent-standard.md",
        {
            "label": label,
            "gatekeeper_upstream_evidence_guidance": gatekeeper_upstream_evidence_guidance,
            "GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE": GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
            "gatekeeper_dynamic_check_guidance": gatekeeper_dynamic_check_guidance,
            "inspector_dynamic_check_guidance": inspector_dynamic_check_guidance,
            "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
        },
    )


def _gatekeeper_upstream_evidence_guidance(role: str) -> str:
    if role != "gatekeeper":
        return ""
    return GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE


def _gatekeeper_dynamic_check_guidance(role: str) -> str:
    if role != "gatekeeper":
        return ""
    return load_system_prompt_asset("agent_native/gatekeeper-dynamic-check.md").strip() + "\n\n"


def _inspector_dynamic_check_guidance(role: str) -> str:
    if role != "inspector":
        return ""
    return (
        render_system_prompt_asset(
            "agent_native/inspector-dynamic-check.md",
            {"INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE": INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE},
        ).strip()
        + "\n\n"
    )


def agent_native_dispatch_guidance(adapter: str) -> str:
    if adapter == "codex":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-codex.md").strip() + "\n"
    if adapter == "claude":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-claude.md").strip() + "\n"
    if adapter == "opencode":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-opencode.md").strip() + "\n"
    return ""
