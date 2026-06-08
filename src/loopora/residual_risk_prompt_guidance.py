from __future__ import annotations

from loopora.system_prompt_assets import load_system_prompt_asset

GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE = load_system_prompt_asset("shared/gatekeeper-residual-risk.md").strip()

GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE = load_system_prompt_asset("shared/gatekeeper-upstream-evidence.md").strip()

AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE = load_system_prompt_asset(
    "shared/agent-plan-residual-risk-skeleton.md"
).strip()
