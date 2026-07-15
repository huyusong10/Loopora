from __future__ import annotations

from typing import Any

from loopora.agent_native_adapter_policies import (
    NATIVE_PROOF_BOUNDARY as NATIVE_PROOF_BOUNDARY,
    NATIVE_RUN_ENTRY_CONTRACT_BULLETS as NATIVE_RUN_ENTRY_CONTRACT_BULLETS,
    NATIVE_RUN_ENTRY_CONTRACT_TITLE as NATIVE_RUN_ENTRY_CONTRACT_TITLE,
    NATIVE_SUBMIT_CONTRACT as NATIVE_SUBMIT_CONTRACT,
    agent_adapter_accepted_native_tools as agent_adapter_accepted_native_tools,
    agent_adapter_native_dispatch_mechanism as agent_adapter_native_dispatch_mechanism,
)
from loopora.agent_native_adapter_policies import (
    AGENT_ADAPTER_KINDS as AGENT_ADAPTER_KINDS,
    normalize_agent_adapter_kind as normalize_agent_adapter_kind,
)
from loopora.agent_native_adapter_policies import (
    ROLE_AGENT_KINDS as ROLE_AGENT_KINDS,
    agent_adapter_context_identity_env as agent_adapter_context_identity_env,
    agent_adapter_context_loading_policy as agent_adapter_context_loading_policy,
    agent_adapter_entry_kind as agent_adapter_entry_kind,
    agent_adapter_entry_paths as agent_adapter_entry_paths,
    agent_adapter_experience_capabilities as agent_adapter_experience_capabilities,
    agent_adapter_handoff_protocol as agent_adapter_handoff_protocol,
    agent_adapter_health_check_policy as agent_adapter_health_check_policy,
    agent_adapter_native_capability_contract as agent_adapter_native_capability_contract,
    agent_adapter_observability_policy as agent_adapter_observability_policy,
    agent_adapter_ownership_boundary as agent_adapter_ownership_boundary,
    agent_adapter_packaging_policy as agent_adapter_packaging_policy,
    agent_adapter_permission_boundary as agent_adapter_permission_boundary,
    agent_adapter_role_agent_map as agent_adapter_role_agent_map,
    agent_adapter_role_agent_paths as agent_adapter_role_agent_paths,
    agent_adapter_session_recovery_policy as agent_adapter_session_recovery_policy,
    agent_adapter_tooling_boundary as agent_adapter_tooling_boundary,
)


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


def agent_adapter_native_surface_summary(adapter: str) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    return {
        "entry_kind": agent_adapter_entry_kind(kind),
        "entry_paths": agent_adapter_entry_paths(kind),
        "capability_contract": agent_adapter_native_capability_contract(kind),
        "slash_commands": {
            "plan": "/loopora-plan",
            "run": "/loopora-run",
        },
        "role_agents": agent_adapter_role_agent_map(kind),
        "context_identity_env": agent_adapter_context_identity_env(kind),
        "packaging": agent_adapter_packaging_policy(kind),
        "context_loading": agent_adapter_context_loading_policy(kind),
        "health_check": agent_adapter_health_check_policy(kind),
        "session_recovery": agent_adapter_session_recovery_policy(kind),
        "handoff_protocol": agent_adapter_handoff_protocol(kind),
        "permission_boundary": agent_adapter_permission_boundary(kind),
        "tooling_boundary": agent_adapter_tooling_boundary(kind),
        "observability": agent_adapter_observability_policy(kind),
        "experience_capabilities": agent_adapter_experience_capabilities(kind),
        "ownership_boundary": agent_adapter_ownership_boundary(kind),
        "native_dispatch": {
            "orchestrator": "loopora-orchestrator",
            "host_mechanism": agent_adapter_native_dispatch_mechanism(kind),
            "accepted_native_tools": agent_adapter_accepted_native_tools(kind),
            "submit_contract": NATIVE_SUBMIT_CONTRACT,
            "proof_boundary": NATIVE_PROOF_BOUNDARY,
            "nested_provider_cli": "not_used",
        },
    }


def agent_adapter_native_run_surface_summary(adapter: str) -> dict[str, Any]:
    surface = agent_adapter_native_surface_summary(adapter)
    role_agents = surface.get("role_agents") if isinstance(surface.get("role_agents"), dict) else {}
    native_dispatch = surface.get("native_dispatch") if isinstance(surface.get("native_dispatch"), dict) else {}
    target_agents = [
        str(item.get("target_agent") or "").strip()
        for item in role_agents.values()
        if isinstance(item, dict) and str(item.get("target_agent") or "").strip()
    ]
    summary: dict[str, Any] = {
        "entry_kind": surface.get("entry_kind"),
        "entry_paths": surface.get("entry_paths"),
        "capability_contract": surface.get("capability_contract"),
        "slash_commands": surface.get("slash_commands"),
        "orchestrator": native_dispatch.get("orchestrator"),
        "target_agents": target_agents,
        "host_mechanism": native_dispatch.get("host_mechanism"),
        "accepted_native_tools": native_dispatch.get("accepted_native_tools"),
        "context_identity_env": surface.get("context_identity_env"),
        "packaging": surface.get("packaging"),
        "context_loading": surface.get("context_loading"),
        "health_check": surface.get("health_check"),
        "session_recovery": surface.get("session_recovery"),
        "handoff_protocol": surface.get("handoff_protocol"),
        "permission_boundary": surface.get("permission_boundary"),
        "tooling_boundary": surface.get("tooling_boundary"),
        "observability": surface.get("observability"),
        "experience_capabilities": surface.get("experience_capabilities"),
        "ownership_boundary": surface.get("ownership_boundary"),
        "submit_contract": native_dispatch.get("submit_contract"),
        "proof_boundary": native_dispatch.get("proof_boundary"),
        "nested_provider_cli": native_dispatch.get("nested_provider_cli"),
    }
    return compact_surface_fields(summary, NATIVE_RUN_SURFACE_FIELDS)
