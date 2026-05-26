from __future__ import annotations

from typing import Any

NATIVE_SURFACE_DICT_SECTIONS = (
    "entry_paths",
    "slash_commands",
    "role_agents",
    "capability_contract",
    "packaging",
    "context_loading",
    "health_check",
    "session_recovery",
    "handoff_protocol",
    "permission_boundary",
    "tooling_boundary",
    "observability",
    "experience_capabilities",
    "ownership_boundary",
)

NATIVE_RUN_SURFACE_FIELDS = (
    "entry_kind",
    "entry_paths",
    "capability_contract",
    "slash_commands",
    "orchestrator",
    "target_agents",
    "host_mechanism",
    "accepted_native_tools",
    "context_identity_env",
    "packaging",
    "context_loading",
    "health_check",
    "session_recovery",
    "handoff_protocol",
    "permission_boundary",
    "tooling_boundary",
    "observability",
    "experience_capabilities",
    "ownership_boundary",
    "submit_contract",
    "proof_boundary",
    "nested_provider_cli",
)


def compact_surface_fields(surface: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: surface.get(key) for key in keys if surface.get(key) not in ("", [], {})}


def surface_dict_sections(surface: dict[str, Any]) -> dict[str, dict]:
    return {key: _surface_dict(surface, key) for key in NATIVE_SURFACE_DICT_SECTIONS}


def _surface_dict(surface: dict[str, Any], key: str) -> dict:
    value = surface.get(key)
    return value if isinstance(value, dict) else {}
