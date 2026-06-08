from __future__ import annotations

from loopora.agent_native_adapter_identity import normalize_agent_adapter_kind
from loopora.service_types import LooporaError
from loopora.system_prompt_assets import load_system_prompt_asset


NATIVE_SUBMIT_CONTRACT = "loopora_host_dispatch + schema-shaped result template"
NATIVE_PROOF_BOUNDARY = "native todo/trace may guide host work; Loopora evidence refs and task verdict remain the proof source"
_NATIVE_RUN_ENTRY_CONTRACT = load_system_prompt_asset("agent_native/run-entry-contract.md")
NATIVE_RUN_ENTRY_CONTRACT_TITLE = _NATIVE_RUN_ENTRY_CONTRACT.splitlines()[0].removeprefix("## ").strip()
NATIVE_RUN_ENTRY_CONTRACT_BULLETS = tuple(
    line.removeprefix("- ").strip() for line in _NATIVE_RUN_ENTRY_CONTRACT.splitlines() if line.startswith("- ")
)


def agent_adapter_accepted_native_tools(adapter: str) -> list[str]:
    try:
        kind = normalize_agent_adapter_kind(adapter)
    except LooporaError:
        return []
    if kind == "codex":
        return ["spawn_agent"]
    if kind == "claude":
        return ["Agent", "Task"]
    if kind == "opencode":
        return ["task"]
    return []


def agent_adapter_native_dispatch_mechanism(adapter: str) -> str:
    try:
        kind = normalize_agent_adapter_kind(adapter)
    except LooporaError:
        return "host-native role agent dispatch"
    if kind == "codex":
        return "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    if kind == "claude":
        return "Claude Code Agent/Task with the named Loopora role agent"
    if kind == "opencode":
        return "OpenCode project command agent=loopora-orchestrator, then native task tool"
    return "host-native role agent dispatch"
