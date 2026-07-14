from __future__ import annotations

from loopora import agent_adapter_command_prefix
from loopora.agent_adapter_role_contracts import agent_native_dispatch_guidance
from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset


def _run_contract_values(*, adapter: str, marker_source: str, context_arg: str = "", context_bits: str = "") -> dict[str, str]:
    resolved_context_bits = context_bits or (f" {context_arg}" if context_arg else "")
    return {
        "adapter": adapter,
        "marker_source": marker_source,
        "loopora_cli_entry": agent_adapter_command_prefix.current_project_file_loopora_cli_entry(),
        "context_bits": resolved_context_bits,
        "dispatch_guidance": agent_native_dispatch_guidance(adapter).rstrip(),
    }


def agent_run_section_overview(*, adapter: str, marker_source: str, context_bits: str) -> str:
    contract = render_system_prompt_asset(
        "agent_native/run-contract.md",
        _run_contract_values(adapter=adapter, marker_source=marker_source, context_bits=context_bits),
    )
    overview = contract.split("## Detailed Contract", 1)[0]
    return overview.removeprefix("# Loopora Run Contract\n\n").rstrip()


def agent_native_loop_body(*, adapter: str, marker_source: str, context_arg: str = "") -> str:
    return render_system_prompt_asset(
        "agent_native/run-contract.md",
        _run_contract_values(adapter=adapter, marker_source=marker_source, context_arg=context_arg),
    )


def agent_native_run_entry_contract() -> str:
    return load_system_prompt_asset("agent_native/run-entry-contract.md")
