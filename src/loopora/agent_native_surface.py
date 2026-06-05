from __future__ import annotations

from typing import Any

from loopora.agent_native_adapter_contracts import agent_adapter_native_run_surface_summary
from loopora.agent_native_surface_lines import native_surface_plain_lines

__all__ = [
    "agent_native_run_surface_for_result",
    "attach_native_run_surface",
    "compact_native_run_surface",
    "native_surface_plain_lines",
]


def attach_native_run_surface(
    summary: dict[str, Any],
    result: dict | None = None,
    *sources: object,
    adapter: str = "",
    compact: bool = False,
) -> None:
    surface = (
        agent_adapter_native_run_surface_summary(adapter)
        if str(adapter or "").strip()
        else agent_native_run_surface_for_result(result or {}, *sources)
    )
    if compact:
        surface = compact_native_run_surface(surface)
    if surface:
        summary["agent_surface"] = surface


def agent_native_run_surface_for_result(result: dict, *sources: object) -> dict[str, Any]:
    adapter = _surface_adapter_from_sources(result, *sources)
    return agent_adapter_native_run_surface_summary(adapter)


def compact_native_run_surface(surface: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(surface, dict):
        return {}
    compact: dict[str, Any] = {}
    for key in (
        "entry_kind",
        "entry_paths",
        "slash_commands",
        "target_agents",
        "host_mechanism",
        "accepted_native_tools",
        "submit_contract",
        "proof_boundary",
        "nested_provider_cli",
    ):
        value = surface.get(key)
        if value not in ("", [], {}, None):
            compact[key] = value
    capability = surface.get("capability_contract") if isinstance(surface.get("capability_contract"), dict) else {}
    compact_capability = {
        key: capability[key]
        for key in (
            "activation",
            "command_namespace",
            "role_dispatch",
            "workspace_owner",
            "proof_owner",
            "nested_provider_cli",
        )
        if capability.get(key) not in ("", [], {}, None)
    }
    if compact_capability:
        compact["capability_contract"] = compact_capability
    experience = surface.get("experience_capabilities") if isinstance(surface.get("experience_capabilities"), dict) else {}
    compact_experience = {
        key: experience[key]
        for key in (
            "role_dispatch_guidance",
            "todo_guidance",
            "native_trace_optional",
            "technical_handoff_paths",
        )
        if experience.get(key) not in ("", [], {}, None)
    }
    if compact_experience:
        compact["experience_capabilities"] = compact_experience
    return compact


def _surface_adapter_from_sources(result: dict, *sources: object) -> str:
    for source in (result, *sources):
        if not isinstance(source, dict):
            continue
        adapter = str(source.get("adapter") or "").strip()
        if adapter:
            return adapter
    return "codex"
