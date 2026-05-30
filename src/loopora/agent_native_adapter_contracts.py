from __future__ import annotations

from typing import Any

from loopora.agent_native_surface_schema import NATIVE_RUN_SURFACE_FIELDS, compact_surface_fields
from loopora.service_types import LooporaError

AGENT_ADAPTER_KINDS = ("codex", "claude", "opencode")
ROLE_AGENT_KINDS = ("builder", "inspector", "gatekeeper", "guide", "orchestrator")
NATIVE_SUBMIT_CONTRACT = "loopora_host_dispatch + schema-shaped result template"
NATIVE_PROOF_BOUNDARY = "native todo/trace may guide host work; Loopora evidence refs and task verdict remain the proof source"
NATIVE_RUN_ENTRY_CONTRACT_TITLE = "Native Run Contract"
NATIVE_RUN_ENTRY_CONTRACT_BULLETS = (
    "Read root `agent_v3_envelope.summary` before raw legacy diagnostics.",
    "Start only from `/loopora-plan`, `/loopora-run`, or explicit Loopora CLI commands; host hooks or session start must not auto-trigger Loopora work.",
    "Dispatch only through the host-native role agent named by `next_step.role_dispatch.target_agent`; if unavailable, stop before submit.",
    "Treat host auto-activation, compatibility routing, or rule injection as context hints, not Loopora dispatch proof.",
    "Use the context, step-contract, and result-template paths for role handoff; do not replace them with a large inline prompt.",
    "Do not copy credentials, API keys, tokens, or environment secrets into result files; use redacted evidence references.",
    "Do not fan out to multiple role agents unless the reviewed Loop workflow exposes a parallel group.",
    "Treat `complete` as run lifecycle only; task proof comes from `task_proven`, `task_outcome`, and `run.task_verdict`.",
    "Use the exact Loopora context card or surfaced recoverable choices; do not auto-discover or take over host historical sessions.",
    "Never start codex, claude, or opencode as nested provider CLIs.",
)


def normalize_agent_adapter_kind(value: str | None) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    aliases = {
        "codex": "codex",
        "openai-codex": "codex",
        "claude": "claude",
        "claude-code": "claude",
        "claudecode": "claude",
        "opencode": "opencode",
        "open-code": "opencode",
    }
    if normalized in aliases:
        return aliases[normalized]
    supported = ", ".join(AGENT_ADAPTER_KINDS)
    raise LooporaError(f"unsupported agent adapter: {value!r}. Expected one of: {supported}")


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


def agent_adapter_native_capability_contract(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "execution_owner": "current_host_agent",
        "activation": "explicit_loopora_command_or_cli_only",
        "command_namespace": "loopora_plan_run_only_no_generic_host_command_aliases",
        "project_entry": "loopora_managed",
        "role_dispatch": "host_native",
        "role_config": "project_local_managed",
        "context_card": "env_or_explicit_context_id",
        "diagnostics": "loopora_check_commands",
        "workspace_owner": "current_host_agent_workdir",
        "worktree_management": "not_created_or_switched_by_loopora",
        "proof_owner": "loopora_evidence_refs_and_task_verdict",
        "nested_provider_cli": "not_used",
    }


def agent_adapter_packaging_policy(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "behavior_source": "loopora_core_and_managed_references",
        "host_entries": "generated_thin_project_local_packaging",
        "projection_policy": "generated_projections_caches_and_marketplace_metadata_are_not_canonical_behavior",
        "component_export": "prompt_wrappers_cross_host_skill_exports_and_external_skill_installers_are_guidance_not_adapter_parity_or_install_proof",
        "install_scope": "project_local_no_global_marketplace_or_skill_cache",
        "entry_visibility": "adapter_project_entries_checked_not_global_skill_sync_assumed",
        "shadow_policy": "stale_duplicate_or_shadow_entries_are_visibility_risks_not_loopora_proof",
        "registry_policy": "remote_marketplaces_are_discovery_not_runtime_dependency_or_proof",
        "link_policy": "global_or_external_symlinks_are_hints_not_loopora_entry_proof",
        "runtime_bundle": "entries_roles_references_and_state_checked_together",
        "manifest": "managed_files_sha256_manifest",
        "drift_check": "loopora_check_reports_missing_stale_or_unowned_files",
        "update_policy": "explicit_check_or_init_only_no_background_auto_update",
        "repair": "regenerate_loopora_managed_packaging_only",
    }


def agent_adapter_context_loading_policy(adapter: str) -> dict[str, list[str] | str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "entry_prompt": "thin_dispatcher",
        "summary_first": [
            "agent_v3_envelope.summary",
        ],
        "reference_loading": "on_demand_from_reference_paths",
        "full_payload": "open_after_compact_summary",
        "host_memory": "host_owned_hint_not_loopora_context_or_evidence",
        "memory_store": "external_memory_stores_indexes_and_memory_mcp_are_hints_not_loopora_context_or_proof",
        "template_context": "host_command_templates_playbooks_and_dynamic_prompts_are_hints_not_loopora_reviewed_workflow",
        "workflow_kits": "external_spec_workflows_prd_packs_quality_gate_recipes_and_workflow_kits_are_guidance_not_loopora_reviewed_workflow_install_proof_or_evidence",
        "role_catalogs": "external_agent_catalogs_subagent_libraries_and_role_marketplaces_are_selection_hints_not_loopora_role_contract_or_policy",
        "compaction_context": "host_compaction_summaries_are_hints_not_loopora_context_or_proof",
        "host_context": "host_loaded_skills_commands_agents_editor_context_and_ide_bridges_are_hints_not_loopora_context_contract_or_evidence",
        "catalog_context": "marketplace_catalogs_and_uninstalled_components_are_not_loopora_context_or_proof",
    }


def agent_adapter_observability_policy(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "agent_activity": "host_status_or_compact_summary_only",
        "web_view": "observe_evidence_gaps_and_verdicts",
        "permission_prompts": "host_agent_owns_approval_flow",
        "hook_events": "observation_only_until_submitted_as_loopora_evidence",
        "hook_protocol": "adapter_specific_no_cross_host_parity_assumption",
        "hook_runners": "external_hook_runners_are_opt_in_host_automation_not_loopora_dispatch",
        "statusline_metrics": "host_statusline_usage_cost_context_and_git_metrics_are_observation_not_loopora_proof",
        "task_trackers": "external_task_managers_todos_backlogs_and_subagent_statuses_are_coordination_not_loopora_lifecycle_or_proof",
        "remote_controls": "ci_actions_pr_bots_comment_triggers_dashboards_webhooks_and_background_consoles_are_host_control_not_loopora_activation_dispatch_or_proof",
        "diagnostic_traces": "external_trace_viewers_api_proxies_session_recorders_and_usage_analyzers_are_diagnostics_not_loopora_evidence_or_verdict",
        "progress_signal": "activity_status_is_not_task_proof",
        "proof_signal": "loopora_evidence_refs_and_task_verdict",
    }


def agent_adapter_experience_capabilities(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "role_dispatch_guidance": "managed_entries_name_the_host_native_role_agent_and_stop_before_inline_submit",
        "todo_guidance": "native_todo_should_create_or_update_host_todo_when_available_not_evidence",
        "user_question_guidance": "ask_user_routes_missing_loop_judgment_to_main_agent_session",
        "native_trace_optional": "preserve_official_subagent_or_task_trace_when_available_do_not_invent",
        "technical_handoff_paths": "context_step_contract_result_template_and_submit_command_remain_available_below_work_panel",
    }


def agent_adapter_tooling_boundary(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "mcp_servers": "host_owned_not_installed_or_enabled_by_loopora",
        "external_tools": "use_host_available_tools_without_relaxing_permissions",
        "tool_outputs": "proof_only_when_submitted_as_loopora_evidence",
    }


def agent_adapter_handoff_protocol(adapter: str) -> dict[str, list[str] | str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "role_channel": "host_native_role_agent",
        "required_context": [
            "role_dispatch.target_agent",
            "context_path",
            "step_contract_path",
            "result_template",
        ],
        "payload_policy": "path_based_context_step_contract_and_template_not_large_inline_prompt",
        "submit_gate": "filled_schema_result_with_loopora_host_dispatch",
        "dispatch_failure": "stop_and_report_dispatch_unavailable_before_submit",
        "parallel_dispatch": "only_when_loop_workflow_declares_parallel_group",
        "behavioral_activation": "host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof",
        "external_orchestration": "host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract",
        "human_handoff": "surface_manual_decision_when_context_or_task_proof_is_ambiguous",
    }


def agent_adapter_permission_boundary(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "policy_owner": "host_agent_and_user",
        "loopora_policy": "do_not_bypass_or_downgrade_host_permissions",
        "role_scope": "use_host_native_role_tool_allowlists",
        "approval_prompts": "pause_for_host_approval_or_report_blocked",
        "mode_switching": "host_agent_user_owned_not_changed_by_loopora",
        "automation": "auto_approvers_full_access_and_no_sandbox_are_host_opt_in_not_loopora_policy",
        "sandbox_runners": "external_containers_devcontainers_microvms_and_remote_runners_are_host_isolation_not_loopora_workspace_permission_or_proof",
        "security_guardrails": "external_security_scanners_guardrails_and_agent_firewalls_are_host_controls_not_loopora_permission_policy_or_evidence",
        "deny_rules": "respect_host_deny_rules_before_loopora_submit",
        "proof_boundary": "approval_is_not_task_evidence",
    }


def agent_adapter_session_recovery_policy(adapter: str) -> dict[str, str]:
    normalize_agent_adapter_kind(adapter)
    return {
        "context_card": "exact_agent_context_card_first",
        "ambiguous": "list_recoverable_contexts_before_running",
        "ready_resume": "/loopora-run option:<recoverable_context_id>",
        "not_ready": "return_to_loopora_plan_or_web_review",
        "provider_session_resume": "not_used_for_loopora_work",
        "host_session_discovery": "not_auto_discovered_or_taken_over_by_loopora",
        "checkpoint_restore": "host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_context_or_proof",
    }


def agent_adapter_health_check_policy(adapter: str) -> dict[str, str]:
    kind = normalize_agent_adapter_kind(adapter)
    return {
        "adapter_check": f"loopora agent {kind} check --workdir <project>",
        "install_check": f"loopora init {kind} --workdir <project> --check",
        "repair": f"loopora init {kind} --workdir <project>",
        "scope": "managed_entries_role_configs_and_loopora_state",
        "side_effects": "check_commands_do_not_install_or_overwrite",
        "host_reload": "restart_or_new_host_session_may_be_required_for_entry_discovery",
    }


def agent_adapter_ownership_boundary(adapter: str) -> dict[str, list[str] | str]:
    kind = normalize_agent_adapter_kind(adapter)
    loopora_owned = [
        "managed_project_entries",
        "project_local_role_agent_configs",
        ".loopora_state",
    ]
    managed_hooks: list[str] = []
    if kind == "claude":
        loopora_owned.append("managed_session_context_hook")
        managed_hooks.append("claude_session_context_hook")
    return {
        "loopora_owned": loopora_owned,
        "managed_hooks": managed_hooks,
        "host_owned": [
            "model_provider_defaults",
            "global_user_config",
            "user_skills_and_plugins",
            "mcp_servers",
            "permissions",
            "unrelated_hooks",
            "credentials_and_environment_secrets",
        ],
        "model_policy": "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof",
        "skill_policy": "host_skills_plugins_not_auto_mutated_by_loopora",
        "credential_policy": "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof",
        "repair_policy": "check_then_reinstall_loopora_managed_entries_only",
    }


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


def agent_adapter_entry_kind(kind: str) -> str:
    if kind == "opencode":
        return "project_command"
    return "project_skill"


def agent_adapter_entry_paths(kind: str) -> dict[str, str]:
    if kind == "codex":
        return {
            "plan": ".agents/skills/loopora-plan/SKILL.md",
            "run": ".agents/skills/loopora-run/SKILL.md",
        }
    if kind == "claude":
        return {
            "plan": ".claude/skills/loopora-plan/SKILL.md",
            "run": ".claude/skills/loopora-run/SKILL.md",
        }
    if kind == "opencode":
        return {
            "plan": ".opencode/commands/loopora-plan.md",
            "run": ".opencode/commands/loopora-run.md",
        }
    return {}


def agent_adapter_role_agent_paths(kind: str) -> dict[str, str]:
    if kind == "codex":
        return {role: f".codex/agents/loopora-{role}.toml" for role in ROLE_AGENT_KINDS}
    if kind == "claude":
        return {role: f".claude/agents/loopora-{role}.md" for role in ROLE_AGENT_KINDS}
    if kind == "opencode":
        return {role: f".opencode/agents/loopora-{role}.md" for role in ROLE_AGENT_KINDS}
    return {}


def agent_adapter_role_agent_map(kind: str) -> dict[str, dict[str, str]]:
    return {
        role: {
            "target_agent": f"loopora-{role}",
            "path": path,
        }
        for role, path in agent_adapter_role_agent_paths(kind).items()
    }


def agent_adapter_context_identity_env(kind: str) -> list[str]:
    if kind == "codex":
        return ["LOOPORA_AGENT_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"]
    if kind == "claude":
        return ["LOOPORA_AGENT_SESSION_ID", "CLAUDE_SESSION_ID"]
    if kind == "opencode":
        return ["LOOPORA_AGENT_SESSION_ID", "OPENCODE_SESSION_ID"]
    return ["LOOPORA_AGENT_SESSION_ID"]
