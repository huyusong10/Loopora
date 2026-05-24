from __future__ import annotations

from loopora.agent_native_adapter_contracts import agent_adapter_native_surface_summary
from loopora.cli_agent_adapter_output import print_adapter_mutation_result


def _assert_output_contains(output: str, *snippets: str) -> None:
    missing = [snippet for snippet in snippets if snippet not in output]
    assert not missing, f"missing output snippets: {missing[:5]}"


def test_adapter_output_keeps_native_surface_and_clean_fallback_steps(tmp_path, capsys) -> None:
    print_adapter_mutation_result(
        {
            "adapter": "codex",
            "label": "Codex",
            "workdir": str(tmp_path),
            "status": "installed",
            "next_commands": {
                "check": "loopora init codex --check",
                "agent_check": "loopora agent codex check",
            },
            "first_task_message_example": "After /loopora-plan, send: Goal: ...",
            "native_surface": {
                **agent_adapter_native_surface_summary("codex"),
                "reference_paths": [
                    ".agents/skills/loopora-run/references/loopora-run-contract.md",
                    ".agents/skills/loopora-run/references/loopora-recovery-matrix.md",
                ],
                "owned_state": [".loopora/", ".loopora/adapters/codex/manifest.json"],
            },
            "managed_files": [
                {
                    "path": ".agents/skills/loopora-plan/SKILL.md",
                    "state": "managed",
                }
            ],
        },
        action="installed",
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Codex Loopora entry is installed" in output
    assert "target project:" in output
    assert "first task message example:" in output
    assert "native surface:" in output
    assert "- slash commands: plan=/loopora-plan run=/loopora-run" in output
    assert (
        "- capabilities: execution=current_host_agent; role_dispatch=host_native; "
        "workspace=current_host_agent_workdir; worktree=not_created_or_switched_by_loopora; "
        "proof=loopora_evidence_refs_and_task_verdict"
    ) in output
    assert "- activation: explicit_loopora_command_or_cli_only" in output
    assert "- command namespace: loopora_plan_run_only_no_generic_host_command_aliases" in output
    assert "- references: .agents/skills/loopora-run/references/loopora-run-contract.md" in output
    for snippet in (
        "- packaging: source=loopora_core_and_managed_references",
        "projections=generated_projections_caches_and_marketplace_metadata_are_not_canonical_behavior",
        "components=prompt_wrappers_cross_host_skill_exports_and_external_skill_installers_are_guidance_not_adapter_parity_or_install_proof",
        "scope=project_local_no_global_marketplace_or_skill_cache",
        "visibility=adapter_project_entries_checked_not_global_skill_sync_assumed",
        "shadow=stale_duplicate_or_shadow_entries_are_visibility_risks_not_loopora_proof",
        "registry=remote_marketplaces_are_discovery_not_runtime_dependency_or_proof",
        "links=global_or_external_symlinks_are_hints_not_loopora_entry_proof",
        "bundle=entries_roles_references_and_state_checked_together",
        "update=explicit_check_or_init_only_no_background_auto_update",
        "repair=regenerate_loopora_managed_packaging_only",
    ):
        assert snippet in output
    _assert_output_contains(
        output,
        "- context loading: entry=thin_dispatcher",
        "full_payload=open_after_compact_summary",
        "memory_store=external_memory_stores_indexes_and_memory_mcp_are_hints_not_loopora_context_or_proof",
        "templates=host_command_templates_playbooks_and_dynamic_prompts_are_hints_not_loopora_reviewed_workflow",
        "workflow_kits=external_spec_workflows_prd_packs_quality_gate_recipes_and_workflow_kits_are_guidance_not_loopora_reviewed_workflow_install_proof_or_evidence",
        "role_catalogs=external_agent_catalogs_subagent_libraries_and_role_marketplaces_are_selection_hints_not_loopora_role_contract_or_policy",
        "compaction=host_compaction_summaries_are_hints_not_loopora_binding_or_proof",
        "host_context=host_loaded_skills_commands_agents_editor_context_and_ide_bridges_are_hints_not_loopora_binding_contract_or_evidence",
        "catalog=marketplace_catalogs_and_uninstalled_components_are_not_loopora_context_or_proof",
        "- health check: adapter=loopora agent codex check --workdir <project>",
        "reload=restart_or_new_host_session_may_be_required_for_entry_discovery",
        "- session recovery: binding=exact_agent_context_binding_first",
        "ready=/loopora-run option:<recoverable_context_id>",
        "host_sessions=not_auto_discovered_or_taken_over_by_loopora",
        "checkpoints=host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_binding_or_proof",
        "- handoff: channel=host_native_role_agent",
        "payload=path_based_context_capsule_and_template_not_large_inline_prompt",
        "behavioral=host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof",
        "external=host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract",
        "human=surface_manual_decision_when_context_or_task_proof_is_ambiguous",
        "- permission boundary: owner=host_agent_and_user",
        "approval=pause_for_host_approval_or_report_blocked",
        "automation=auto_approvers_full_access_and_no_sandbox_are_host_opt_in_not_loopora_policy",
        "sandboxes=external_containers_devcontainers_microvms_and_remote_runners_are_host_isolation_not_loopora_workspace_permission_or_proof",
        "guardrails=external_security_scanners_guardrails_and_agent_firewalls_are_host_controls_not_loopora_permission_policy_or_evidence",
        "- observability: activity=host_status_or_compact_summary_only",
        "permissions=host_agent_owns_approval_flow",
        "hook_protocol=adapter_specific_no_cross_host_parity_assumption",
        "hook_runners=external_hook_runners_are_opt_in_host_automation_not_loopora_dispatch",
        "statusline=host_statusline_usage_cost_context_and_git_metrics_are_observation_not_loopora_proof",
        "task_trackers=external_task_managers_todos_backlogs_and_subagent_statuses_are_coordination_not_loopora_lifecycle_or_proof",
        "remote_controls=ci_actions_pr_bots_comment_triggers_dashboards_webhooks_and_background_consoles_are_host_control_not_loopora_activation_dispatch_or_proof",
        "diagnostic_traces=external_trace_viewers_api_proxies_session_recorders_and_usage_analyzers_are_diagnostics_not_loopora_evidence_or_verdict",
        "- owned state: .loopora/, .loopora/adapters/codex/manifest.json",
        "- ownership: loopora=managed_project_entries, project_local_role_agent_configs, .loopora_state",
        "models=external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof",
        "credentials=host_credentials_env_and_secrets_not_collected_or_used_as_task_proof",
        "repair=check_then_reinstall_loopora_managed_entries_only",
        "- host dispatch: Codex spawn_agent with agent_type=<role_dispatch.target_agent>",
        "- accepted native tools: spawn_agent",
        "- If /loopora-plan or /loopora-run is not visible in Codex",
    )
    assert "{label}" not in output
    assert "managed files:" in output
