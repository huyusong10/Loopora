from __future__ import annotations



from agent_adapter_expected import (
    EXPECTED_NATIVE_EXPERIENCE_CAPABILITIES,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
)
from agent_adapter_test_common import (
    _assert_output_contains,
    _assert_native_context_loading,
)


def _assert_codex_native_surface_summary(summary: dict) -> None:
    surface = summary["native_surface"]
    assert surface["entry_kind"] == "project_skill"
    assert surface["entry_paths"]["plan"] == ".agents/skills/loopora-plan/SKILL.md"
    assert surface["slash_commands"] == {"plan": "/loopora-plan", "run": "/loopora-run"}
    assert surface["orchestrator"] == "loopora-orchestrator"
    assert surface["capability_contract"]["execution_owner"] == "current_host_agent"
    assert surface["capability_contract"]["activation"] == "explicit_loopora_command_or_cli_only"
    assert surface["capability_contract"]["command_namespace"] == "loopora_plan_run_only_no_generic_host_command_aliases"
    assert surface["capability_contract"]["role_dispatch"] == "host_native"
    assert surface["capability_contract"]["workspace_owner"] == "current_host_agent_workdir"
    assert surface["capability_contract"]["worktree_management"] == "not_created_or_switched_by_loopora"
    assert surface["capability_contract"]["proof_owner"] == "loopora_evidence_refs_and_task_verdict"
    assert "loopora-builder" in surface["target_agents"]
    assert surface["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert surface["accepted_native_tools"] == ["spawn_agent"]
    assert surface["packaging"] == EXPECTED_NATIVE_PACKAGING
    _assert_native_context_loading(surface, summary_key="agent_run_summary")
    assert surface["health_check"]["adapter_check"] == "loopora agent codex check --workdir <project>"
    assert surface["health_check"]["scope"] == "managed_entries_role_configs_and_loopora_state"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"
    assert surface["session_recovery"]["binding"] == "exact_agent_context_binding_first"
    assert surface["session_recovery"]["ready_resume"] == "/loopora-run option:<recoverable_context_id>"
    assert (
        surface["session_recovery"]["host_session_discovery"]
        == "not_auto_discovered_or_taken_over_by_loopora"
    )
    assert (
        surface["session_recovery"]["checkpoint_restore"]
        == "host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_binding_or_proof"
    )
    assert surface["handoff_protocol"]["role_channel"] == "host_native_role_agent"
    assert surface["handoff_protocol"]["payload_policy"] == "path_based_context_capsule_and_template_not_large_inline_prompt"
    assert surface["handoff_protocol"]["dispatch_failure"] == "stop_and_report_dispatch_unavailable_before_submit"
    assert surface["handoff_protocol"]["parallel_dispatch"] == "only_when_loop_workflow_declares_parallel_group"
    assert surface["handoff_protocol"]["external_orchestration"] == (
        "host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract"
    )
    assert (
        surface["handoff_protocol"]["behavioral_activation"]
        == "host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof"
    )
    _assert_codex_native_surface_runtime_boundaries(surface)
    assert surface["experience_capabilities"] == EXPECTED_NATIVE_EXPERIENCE_CAPABILITIES
    _assert_codex_native_surface_ownership(surface)
    assert "CODEX_SESSION_ID" in surface["context_identity_env"]
    assert surface["submit_contract"] == "loopora_host_dispatch + schema-shaped result template"
    assert surface["nested_provider_cli"] == "not_used"
    assert "Loopora evidence refs" in surface["proof_boundary"]

def _assert_codex_native_surface_runtime_boundaries(surface: dict) -> None:
    assert surface["permission_boundary"] == EXPECTED_NATIVE_PERMISSION_BOUNDARY
    assert surface["tooling_boundary"] == EXPECTED_NATIVE_TOOLING_BOUNDARY
    assert surface["observability"] == EXPECTED_NATIVE_OBSERVABILITY

def _assert_codex_native_surface_ownership(surface: dict) -> None:
    ownership = surface["ownership_boundary"]
    assert ownership["loopora_owned"] == [
        "managed_project_entries",
        "project_local_role_agent_configs",
        ".loopora_state",
    ]
    assert ownership["managed_hooks"] == []
    assert "permissions" in ownership["host_owned"]
    assert "user_skills_and_plugins" in ownership["host_owned"]
    assert "credentials_and_environment_secrets" in ownership["host_owned"]
    assert (
        ownership["model_policy"]
        == "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof"
    )
    assert ownership["skill_policy"] == "host_skills_plugins_not_auto_mutated_by_loopora"
    assert ownership["credential_policy"] == "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof"
    assert ownership["repair_policy"] == "check_then_reinstall_loopora_managed_entries_only"

def _assert_codex_native_surface_plain(output: str) -> None:
    assert "native surface:" in output
    assert "- entry: project_skill plan=.agents/skills/loopora-plan/SKILL.md run=.agents/skills/loopora-run/SKILL.md" in output
    assert "- slash commands: plan=/loopora-plan run=/loopora-run" in output
    assert "- dispatch: loopora-orchestrator -> loopora-builder" in output
    assert "nested provider CLI=not_used" in output
    assert (
        "- capabilities: execution=current_host_agent; role_dispatch=host_native; "
        "workspace=current_host_agent_workdir; worktree=not_created_or_switched_by_loopora; "
        "proof=loopora_evidence_refs_and_task_verdict"
    ) in output
    assert "- activation: explicit_loopora_command_or_cli_only" in output
    assert "- command namespace: loopora_plan_run_only_no_generic_host_command_aliases" in output
    assert "- host dispatch: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output
    assert "- accepted native tools: spawn_agent" in output
    _assert_output_contains(
        output,
        "- packaging: source=loopora_core_and_managed_references",
        "projections=generated_projections_caches_and_marketplace_metadata_are_not_canonical_behavior",
        "components=prompt_wrappers_cross_host_skill_exports_and_external_skill_installers_are_guidance_not_adapter_parity_or_install_proof",
        "scope=project_local_no_global_marketplace_or_skill_cache",
        "visibility=adapter_project_entries_checked_not_global_skill_sync_assumed",
        "shadow=stale_duplicate_or_shadow_entries_are_visibility_risks_not_loopora_proof",
        "registry=remote_marketplaces_are_discovery_not_runtime_dependency_or_proof",
        "links=global_or_external_symlinks_are_hints_not_loopora_entry_proof",
        "bundle=entries_roles_references_and_state_checked_together",
        "manifest=managed_files_sha256_manifest",
        "drift=loopora_check_reports_missing_stale_or_unowned_files",
        "update=explicit_check_or_init_only_no_background_auto_update",
    )
    _assert_output_contains(
        output,
        "- context loading: entry=thin_dispatcher",
        "summary_first=agent_v3_envelope.summary",
        "references=on_demand_from_reference_paths",
        "memory=host_owned_hint_not_binding_or_evidence",
        "memory_store=external_memory_stores_indexes_and_memory_mcp_are_hints_not_loopora_context_or_proof",
        "templates=host_command_templates_playbooks_and_dynamic_prompts_are_hints_not_loopora_reviewed_workflow",
        "workflow_kits=external_spec_workflows_prd_packs_quality_gate_recipes_and_workflow_kits_are_guidance_not_loopora_reviewed_workflow_install_proof_or_evidence",
        "role_catalogs=external_agent_catalogs_subagent_libraries_and_role_marketplaces_are_selection_hints_not_loopora_role_contract_or_policy",
        "compaction=host_compaction_summaries_are_hints_not_loopora_binding_or_proof",
        "host_context=host_loaded_skills_commands_agents_editor_context_and_ide_bridges_are_hints_not_loopora_binding_contract_or_evidence",
        "catalog=marketplace_catalogs_and_uninstalled_components_are_not_loopora_context_or_proof",
    )
    assert "- health check: adapter=loopora agent codex check --workdir <project>" in output
    assert "side_effects=check_commands_do_not_install_or_overwrite" in output
    assert "reload=restart_or_new_host_session_may_be_required_for_entry_discovery" in output
    assert "- session recovery: binding=exact_agent_context_binding_first" in output
    assert "ambiguous=list_recoverable_contexts_before_running" in output
    assert "provider_resume=not_used_for_loopora_work" in output
    assert "host_sessions=not_auto_discovered_or_taken_over_by_loopora" in output
    assert "checkpoints=host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_binding_or_proof" in output
    _assert_output_contains(
        output,
        "- handoff: channel=host_native_role_agent",
        "required=role_dispatch.target_agent, context_path, capsule_path, result_template",
        "payload=path_based_context_capsule_and_template_not_large_inline_prompt",
        "dispatch_failure=stop_and_report_dispatch_unavailable_before_submit",
        "parallel=only_when_loop_workflow_declares_parallel_group",
        "external=host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract",
        "behavioral=host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof",
    )
    _assert_codex_native_surface_plain_runtime(output)
    _assert_output_contains(
        output,
        "- experience: role_dispatch=managed_entries_name_the_host_native_role_agent_and_stop_before_inline_submit",
        "todo=native_todo_should_create_or_update_host_todo_when_available_not_evidence",
        "user_question=ask_user_routes_missing_loop_judgment_to_main_agent_session",
        "trace=preserve_official_subagent_or_task_trace_when_available_do_not_invent",
        "technical_handoff=context_capsule_result_template_and_submit_command_remain_available_below_work_panel",
    )
    _assert_codex_native_surface_plain_ownership(output)
    assert "- submit contract: loopora_host_dispatch + schema-shaped result template" in output
    assert "- context identity: " in output
    assert "CODEX_SESSION_ID" in output
    assert "- proof boundary: native todo/trace may guide host work; Loopora evidence refs" in output

def _assert_codex_native_surface_plain_runtime(output: str) -> None:
    _assert_output_contains(
        output,
        "- permission boundary: owner=host_agent_and_user",
        "loopora=do_not_bypass_or_downgrade_host_permissions",
        "mode=host_agent_user_owned_not_changed_by_loopora",
        "automation=auto_approvers_full_access_and_no_sandbox_are_host_opt_in_not_loopora_policy",
        "sandboxes=external_containers_devcontainers_microvms_and_remote_runners_are_host_isolation_not_loopora_workspace_permission_or_proof",
        "guardrails=external_security_scanners_guardrails_and_agent_firewalls_are_host_controls_not_loopora_permission_policy_or_evidence",
        "proof=approval_is_not_task_evidence",
        "- tooling boundary: mcp=host_owned_not_installed_or_enabled_by_loopora",
        "tools=use_host_available_tools_without_relaxing_permissions",
        "proof=proof_only_when_submitted_as_loopora_evidence",
        "- observability: activity=host_status_or_compact_summary_only",
        "hooks=observation_only_until_submitted_as_loopora_evidence",
        "hook_protocol=adapter_specific_no_cross_host_parity_assumption",
        "hook_runners=external_hook_runners_are_opt_in_host_automation_not_loopora_dispatch",
        "statusline=host_statusline_usage_cost_context_and_git_metrics_are_observation_not_loopora_proof",
        "task_trackers=external_task_managers_todos_backlogs_and_subagent_statuses_are_coordination_not_loopora_lifecycle_or_proof",
        "remote_controls=ci_actions_pr_bots_comment_triggers_dashboards_webhooks_and_background_consoles_are_host_control_not_loopora_activation_dispatch_or_proof",
        "diagnostic_traces=external_trace_viewers_api_proxies_session_recorders_and_usage_analyzers_are_diagnostics_not_loopora_evidence_or_verdict",
        "progress=activity_status_is_not_task_proof",
        "proof=loopora_evidence_refs_and_task_verdict",
    )

def _assert_codex_native_surface_plain_ownership(output: str) -> None:
    _assert_output_contains(
        output,
        "- ownership: loopora=managed_project_entries, project_local_role_agent_configs, .loopora_state",
        "host=model_provider_defaults, global_user_config, user_skills_and_plugins, mcp_servers, permissions",
        "models=external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof",
        "skills=host_skills_plugins_not_auto_mutated_by_loopora",
        "credentials=host_credentials_env_and_secrets_not_collected_or_used_as_task_proof",
    )
    assert "hooks=claude_session_context_hook" not in output
