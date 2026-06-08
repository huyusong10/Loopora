from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_adapter_contracts import (
    agent_adapter_accepted_native_tools,
    agent_adapter_native_dispatch_mechanism,
)
from loopora.system_prompt_assets import load_system_prompt_asset

ACCEPTED_NATIVE_DISPATCH_MODES = ("host_subagent", "host_task", "host_agent")
ROLE_ARCHETYPE_TARGET_AGENTS = {
    "builder": "loopora-builder",
    "gatekeeper": "loopora-gatekeeper",
    "guide": "loopora-guide",
}
TEMPLATE_ROLE_DISPATCH_KEYS = (
    "dispatch_contract",
    "target_agent",
    "target_role_archetype",
    "inline_allowed",
    "proof_field",
    "result_field",
    "accepted_dispatch_modes",
    "host_mechanism",
    "accepted_native_tools",
)


def agent_native_role_dispatch(*, adapter: str, role_archetype: str, workdir_path: Path) -> dict[str, Any]:
    target_agent = agent_native_target_agent(role_archetype)
    config_path = agent_native_target_agent_config_path(adapter, target_agent)
    absolute_path = str((workdir_path / config_path).resolve()) if config_path else ""
    return {
        "required": True,
        "dispatch_contract": "host_native_subagent",
        "target_agent": target_agent,
        "target_agent_config_path": config_path,
        "target_agent_config_absolute_path": absolute_path,
        "target_agent_config_exists": Path(absolute_path).exists() if absolute_path else False,
        "target_role_archetype": role_archetype,
        "inline_allowed": False,
        "proof_field": "loopora_host_dispatch",
        "result_field": "result",
        "accepted_dispatch_modes": list(ACCEPTED_NATIVE_DISPATCH_MODES),
        "host_mechanism": agent_adapter_native_dispatch_mechanism(adapter),
        "accepted_native_tools": agent_native_accepted_native_tools(adapter),
        "native_trace_contract": agent_native_trace_contract(),
    }


def agent_native_target_agent(archetype: str) -> str:
    normalized = str(archetype or "").strip().lower()
    return ROLE_ARCHETYPE_TARGET_AGENTS.get(normalized, "loopora-inspector")


def agent_native_target_agent_config_path(adapter: str, target_agent: str) -> str:
    normalized_adapter = str(adapter or "").strip().lower()
    normalized_agent = str(target_agent or "").strip()
    if not normalized_agent:
        return ""
    if normalized_adapter == "codex":
        return f".codex/agents/{normalized_agent}.toml"
    if normalized_adapter == "claude":
        return f".claude/agents/{normalized_agent}.md"
    if normalized_adapter == "opencode":
        return f".opencode/agents/{normalized_agent}.md"
    return ""


def agent_native_template_role_dispatch(dispatch: dict[str, Any]) -> dict[str, Any]:
    summary = {key: dispatch.get(key) for key in TEMPLATE_ROLE_DISPATCH_KEYS if dispatch.get(key) not in ("", [], {})}
    return {key: value for key, value in summary.items() if value is not None}


def agent_native_accepted_native_tools(adapter: str) -> list[str]:
    return agent_adapter_accepted_native_tools(adapter)


def agent_native_trace_contract() -> dict[str, Any]:
    return {
        "optional": True,
        "field": "native_trace",
        "trace_ref_field": "native_trace_ref",
        "tool_name_field": "native_tool_name",
        "purpose": load_system_prompt_asset("agent_native/native-trace-contract-purpose.md").strip(),
    }
