from __future__ import annotations

from loopora.agent_native_surface_line_helpers import (
    _compact_string_list,
    _native_surface_dispatch_detail_lines,
    _native_surface_reference_lines,
    _native_surface_role_config_refs,
    _native_surface_target_agents,
)
from loopora.agent_native_surface_schema import surface_dict_sections
from loopora.agent_native_surface_section_lines import (
    _native_surface_context_loading_lines,
    _native_surface_experience_lines,
    _native_surface_handoff_protocol_lines,
    _native_surface_health_check_lines,
    _native_surface_observability_lines,
    _native_surface_ownership_lines,
    _native_surface_packaging_lines,
    _native_surface_permission_boundary_lines,
    _native_surface_session_recovery_lines,
    _native_surface_tooling_boundary_lines,
)


def native_surface_plain_lines(surface: dict, *, include_role_configs: bool = False) -> list[str]:
    if not surface:
        return []
    fields = _native_surface_dict_fields(surface)
    context_env = [str(item).strip() for item in list(surface.get("context_identity_env") or []) if str(item).strip()]

    lines = ["agent surface:"]
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
    lines.extend(_native_surface_experience_lines(fields["experience_capabilities"]))
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
        return [f"- execution: nested provider CLI={nested_provider_cli}"] if nested_provider_cli else []
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
