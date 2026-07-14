from __future__ import annotations

from loopora import agent_adapter_command_prefix
from loopora.agent_adapter_role_contracts import agent_native_dispatch_guidance
from loopora.agent_adapter_run_contract import (
    agent_native_loop_body as agent_native_loop_body,
    agent_native_run_entry_contract as agent_native_run_entry_contract,
    agent_run_section_overview as agent_run_section_overview,
)
from loopora.residual_risk_prompt_guidance import AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE
from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset


def agent_plan_contract(
    adapter: str,
    adapter_label: str,
    marker_source: str,
    *,
    context_arg: str = "",
    supports_arguments: bool = False,
) -> str:
    context_bits = f" {context_arg}" if context_arg else ""
    argument_asset = "agent_native/plan-arguments-host.md" if supports_arguments else "agent_native/plan-arguments-user.md"
    return render_system_prompt_asset(
        "agent_native/plan-contract.md",
        {
            "adapter": adapter,
            "adapter_label": adapter_label,
            "marker_source": marker_source,
            "loopora_cli_entry": agent_adapter_command_prefix.current_project_file_loopora_cli_entry(),
            "context_bits": context_bits,
            "argument_text": load_system_prompt_asset(argument_asset).strip(),
            "AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE": AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE,
        },
    )


def agent_recovery_matrix() -> str:
    return load_system_prompt_asset("agent_native/recovery-matrix.md")


def agent_result_template_guide(adapter: str) -> str:
    return render_system_prompt_asset("agent_native/result-template-guide.md", {"adapter": adapter})


def agent_role_dispatch_guide(adapter: str) -> str:
    dispatch_guidance = agent_native_dispatch_guidance(adapter).strip()
    extra = f"\n\n{dispatch_guidance}" if dispatch_guidance else ""
    return render_system_prompt_asset(
        "agent_native/role-dispatch-guide.md",
        {
            "adapter": adapter,
            "dispatch_guidance_extra": extra,
        },
    )
