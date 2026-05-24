from __future__ import annotations

from typing import Any

from loopora.agent_native_adapter_contracts import agent_adapter_native_run_surface_summary
from loopora.agent_native_surface_schema import surface_dict_sections


def attach_native_run_surface(summary: dict[str, Any], result: dict | None = None, *sources: object, adapter: str = "") -> None:
    surface = (
        agent_adapter_native_run_surface_summary(adapter)
        if str(adapter or "").strip()
        else agent_native_run_surface_for_result(result or {}, *sources)
    )
    if surface:
        summary["native_surface"] = surface


def agent_native_run_surface_for_result(result: dict, *sources: object) -> dict[str, Any]:
    adapter = _surface_adapter_from_sources(result, *sources)
    return agent_adapter_native_run_surface_summary(adapter)


def native_surface_plain_lines(surface: dict, *, include_role_configs: bool = False) -> list[str]:
    if not surface:
        return []
    fields = _native_surface_dict_fields(surface)
    context_env = [str(item).strip() for item in list(surface.get("context_identity_env") or []) if str(item).strip()]

    lines = ["native surface:"]
    lines.extend(_native_surface_entry_lines(surface, fields["entry_paths"]))
    lines.extend(_native_surface_slash_command_lines(fields["slash_commands"]))
    lines.extend(_native_surface_dispatch_lines(surface, fields["dispatch"]))
    lines.extend(_native_surface_capability_lines(fields["capability_contract"]))
    lines.extend(_native_surface_dispatch_detail_lines(surface, fields["dispatch"]))
    lines.extend(_native_surface_role_config_lines(fields["role_agents"], include=include_role_configs))
    lines.extend(_native_surface_reference_lines(surface))
    lines.extend(_native_surface_packaging_lines(fields["packaging"]))
    lines.extend(_native_surface_context_loading_lines(fields["context_loading"]))
    lines.extend(_native_surface_health_check_lines(fields["health_check"]))
    lines.extend(_native_surface_session_recovery_lines(fields["session_recovery"]))
    lines.extend(_native_surface_handoff_protocol_lines(fields["handoff_protocol"]))
    lines.extend(_native_surface_permission_boundary_lines(fields["permission_boundary"]))
    lines.extend(_native_surface_tooling_boundary_lines(fields["tooling_boundary"]))
    lines.extend(_native_surface_observability_lines(fields["observability"]))
    lines.extend(_native_surface_owned_state_lines(surface))
    lines.extend(_native_surface_ownership_lines(fields["ownership_boundary"]))
    lines.extend(_native_surface_tail_lines(fields["dispatch"], context_env))
    return lines


def _native_surface_dict_fields(surface: dict) -> dict[str, dict]:
    fields = surface_dict_sections(surface)
    fields["dispatch"] = surface.get("native_dispatch") if isinstance(surface.get("native_dispatch"), dict) else surface
    return fields


def _native_surface_entry_lines(surface: dict, entry_paths: dict) -> list[str]:
    plan_path = str(entry_paths.get("plan") or "").strip()
    run_path = str(entry_paths.get("run") or "").strip()
    if not (plan_path or run_path):
        return []
    return [f"- entry: {surface.get('entry_kind')} plan={plan_path} run={run_path}"]


def _native_surface_dispatch_lines(surface: dict, dispatch: dict) -> list[str]:
    orchestrator = str(dispatch.get("orchestrator") or "").strip()
    nested_provider_cli = str(dispatch.get("nested_provider_cli") or "").strip()
    targets = _native_surface_target_agents(surface)
    if not (orchestrator and targets):
        return []
    nested_note = f"; nested provider CLI={nested_provider_cli}" if nested_provider_cli else ""
    return [f"- dispatch: {orchestrator} -> {', '.join(targets[:4])}{nested_note}"]


def _native_surface_role_config_lines(role_agents: dict, *, include: bool) -> list[str]:
    if not include:
        return []
    role_config_refs = _native_surface_role_config_refs(role_agents)
    if not role_config_refs:
        return []
    return [f"- role configs: {', '.join(role_config_refs[:4])}"]


def _native_surface_tail_lines(dispatch: dict, context_env: list[str]) -> list[str]:
    lines = []
    submit_contract = str(dispatch.get("submit_contract") or "").strip()
    proof_boundary = str(dispatch.get("proof_boundary") or "").strip()
    if submit_contract:
        lines.append(f"- submit contract: {submit_contract}")
    if context_env:
        lines.append(f"- context identity: {', '.join(context_env)}")
    if proof_boundary:
        lines.append(f"- proof boundary: {proof_boundary}")
    return lines


def _native_surface_slash_command_lines(slash_commands: dict) -> list[str]:
    plan = str(slash_commands.get("plan") or "").strip()
    run = str(slash_commands.get("run") or "").strip()
    if not (plan or run):
        return []
    fields = []
    if plan:
        fields.append(f"plan={plan}")
    if run:
        fields.append(f"run={run}")
    return ["- slash commands: " + " ".join(fields)]


def _native_surface_capability_lines(capability_contract: dict) -> list[str]:
    execution_owner = str(capability_contract.get("execution_owner") or "").strip()
    activation = str(capability_contract.get("activation") or "").strip()
    command_namespace = str(capability_contract.get("command_namespace") or "").strip()
    role_dispatch = str(capability_contract.get("role_dispatch") or "").strip()
    workspace_owner = str(capability_contract.get("workspace_owner") or "").strip()
    worktree_management = str(capability_contract.get("worktree_management") or "").strip()
    proof_owner = str(capability_contract.get("proof_owner") or "").strip()
    if not (
        execution_owner or activation or command_namespace or role_dispatch or workspace_owner or worktree_management or proof_owner
    ):
        return []
    fields = []
    if execution_owner:
        fields.append(f"execution={execution_owner}")
    if role_dispatch:
        fields.append(f"role_dispatch={role_dispatch}")
    if workspace_owner:
        fields.append(f"workspace={workspace_owner}")
    if worktree_management:
        fields.append(f"worktree={worktree_management}")
    if proof_owner:
        fields.append(f"proof={proof_owner}")
    lines = ["- capabilities: " + "; ".join(fields)] if fields else []
    if activation:
        lines.append(f"- activation: {activation}")
    if command_namespace:
        lines.append(f"- command namespace: {command_namespace}")
    return lines


def _native_surface_owned_state_lines(surface: dict) -> list[str]:
    owned_state = _compact_string_list(surface.get("owned_state"))
    if not owned_state:
        return []
    return ["- owned state: " + ", ".join(owned_state[:4])]


def _native_surface_packaging_lines(packaging: dict) -> list[str]:
    return _native_surface_kv_line(
        "packaging",
        packaging,
        (
            ("source", "behavior_source"),
            ("entries", "host_entries"),
            ("projections", "projection_policy"),
            ("components", "component_export"),
            ("scope", "install_scope"),
            ("visibility", "entry_visibility"),
            ("shadow", "shadow_policy"),
            ("registry", "registry_policy"),
            ("links", "link_policy"),
            ("bundle", "runtime_bundle"),
            ("manifest", "manifest"),
            ("drift", "drift_check"),
            ("update", "update_policy"),
            ("repair", "repair"),
        ),
    )


def _native_surface_context_loading_lines(context_loading: dict) -> list[str]:
    return _native_surface_kv_line(
        "context loading",
        context_loading,
        (
            ("entry", "entry_prompt"),
            ("summary_first", "summary_first"),
            ("references", "reference_loading"),
            ("full_payload", "full_payload"),
            ("memory", "host_memory"),
            ("memory_store", "memory_store"),
            ("templates", "template_context"),
            ("workflow_kits", "workflow_kits"),
            ("role_catalogs", "role_catalogs"),
            ("compaction", "compaction_context"),
            ("host_context", "host_context"),
            ("catalog", "catalog_context"),
        ),
    )


def _native_surface_health_check_lines(health_check: dict) -> list[str]:
    return _native_surface_kv_line(
        "health check",
        health_check,
        (
            ("adapter", "adapter_check"),
            ("install", "install_check"),
            ("repair", "repair"),
            ("scope", "scope"),
            ("side_effects", "side_effects"),
            ("reload", "host_reload"),
        ),
    )


def _native_surface_session_recovery_lines(session_recovery: dict) -> list[str]:
    return _native_surface_kv_line(
        "session recovery",
        session_recovery,
        (
            ("binding", "binding"),
            ("ambiguous", "ambiguous"),
            ("ready", "ready_resume"),
            ("not_ready", "not_ready"),
            ("provider_resume", "provider_session_resume"),
            ("host_sessions", "host_session_discovery"),
            ("checkpoints", "checkpoint_restore"),
        ),
    )


def _native_surface_handoff_protocol_lines(handoff_protocol: dict) -> list[str]:
    return _native_surface_kv_line(
        "handoff",
        handoff_protocol,
        (
            ("channel", "role_channel"),
            ("required", "required_context"),
            ("payload", "payload_policy"),
            ("submit", "submit_gate"),
            ("dispatch_failure", "dispatch_failure"),
            ("parallel", "parallel_dispatch"),
            ("behavioral", "behavioral_activation"),
            ("external", "external_orchestration"),
            ("human", "human_handoff"),
        ),
    )


def _native_surface_permission_boundary_lines(permission_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "permission boundary",
        permission_boundary,
        (
            ("owner", "policy_owner"),
            ("loopora", "loopora_policy"),
            ("roles", "role_scope"),
            ("approval", "approval_prompts"),
            ("mode", "mode_switching"),
            ("automation", "automation"),
            ("sandboxes", "sandbox_runners"),
            ("guardrails", "security_guardrails"),
            ("deny", "deny_rules"),
            ("proof", "proof_boundary"),
        ),
    )


def _native_surface_observability_lines(observability: dict) -> list[str]:
    return _native_surface_kv_line(
        "observability",
        observability,
        (
            ("activity", "agent_activity"),
            ("web", "web_view"),
            ("permissions", "permission_prompts"),
            ("hooks", "hook_events"),
            ("hook_protocol", "hook_protocol"),
            ("hook_runners", "hook_runners"),
            ("statusline", "statusline_metrics"),
            ("task_trackers", "task_trackers"),
            ("remote_controls", "remote_controls"),
            ("diagnostic_traces", "diagnostic_traces"),
            ("progress", "progress_signal"),
            ("proof", "proof_signal"),
        ),
    )


def _native_surface_tooling_boundary_lines(tooling_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "tooling boundary",
        tooling_boundary,
        (
            ("mcp", "mcp_servers"),
            ("tools", "external_tools"),
            ("proof", "tool_outputs"),
        ),
    )


def _native_surface_ownership_lines(ownership_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "ownership",
        ownership_boundary,
        (
            ("loopora", "loopora_owned"),
            ("hooks", "managed_hooks"),
            ("host", "host_owned"),
            ("models", "model_policy"),
            ("skills", "skill_policy"),
            ("credentials", "credential_policy"),
            ("repair", "repair_policy"),
        ),
    )


def _native_surface_kv_line(
    title: str,
    source: dict,
    fields: tuple[tuple[str, str], ...],
) -> list[str]:
    rendered = []
    for label, key in fields:
        value = _native_surface_field_value(source.get(key))
        if value:
            rendered.append(f"{label}={value}")
    if not rendered:
        return []
    return [f"- {title}: " + "; ".join(rendered)]


def _native_surface_field_value(value: object) -> str:
    values = _compact_string_list(value)
    if values:
        return ", ".join(values[:5])
    return str(value or "").strip() if not isinstance(value, (list, tuple, set)) else ""


def _compact_string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _native_surface_reference_lines(surface: dict) -> list[str]:
    references = _compact_string_list(surface.get("reference_paths"))
    if not references:
        return []
    return ["- references: " + ", ".join(references[:4])]


def _native_surface_dispatch_detail_lines(surface: dict, dispatch: dict) -> list[str]:
    host_mechanism = str(dispatch.get("host_mechanism") or surface.get("host_mechanism") or "").strip()
    native_tools = [
        str(item).strip()
        for item in list(dispatch.get("accepted_native_tools") or surface.get("accepted_native_tools") or [])
        if str(item).strip()
    ]
    lines: list[str] = []
    if host_mechanism:
        lines.append(f"- host dispatch: {host_mechanism}")
    if native_tools:
        lines.append(f"- accepted native tools: {', '.join(native_tools)}")
    return lines


def _surface_adapter_from_sources(result: dict, *sources: object) -> str:
    for source in (result, *sources):
        if not isinstance(source, dict):
            continue
        adapter = str(source.get("adapter") or "").strip()
        if adapter:
            return adapter
    return "codex"


def _native_surface_target_agents(surface: dict) -> list[str]:
    targets = [str(item).strip() for item in list(surface.get("target_agents") or []) if str(item).strip()]
    if targets:
        return targets
    role_agents = surface.get("role_agents") if isinstance(surface.get("role_agents"), dict) else {}
    return [
        str(item.get("target_agent") or "").strip()
        for item in role_agents.values()
        if isinstance(item, dict) and str(item.get("target_agent") or "").strip()
    ]


def _native_surface_role_config_refs(role_agents: dict) -> list[str]:
    return [
        f"{str(item.get('target_agent') or '').strip()}={str(item.get('path') or '').strip()}"
        for item in role_agents.values()
        if isinstance(item, dict) and str(item.get("target_agent") or "").strip() and str(item.get("path") or "").strip()
    ]
