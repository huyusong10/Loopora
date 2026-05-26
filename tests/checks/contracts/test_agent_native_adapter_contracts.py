from __future__ import annotations

import pytest

from loopora.agent_adapters import normalize_agent_adapter_kind as legacy_normalize_agent_adapter_kind
from loopora.agent_native_adapter_contracts import (
    agent_adapter_context_identity_env,
    agent_adapter_native_capability_contract,
    agent_adapter_native_run_surface_summary,
    agent_adapter_native_surface_summary,
    normalize_agent_adapter_kind,
)
from loopora.service_types import LooporaError


def test_agent_native_adapter_contracts_normalize_host_aliases_without_installer_state() -> None:
    assert normalize_agent_adapter_kind("openai-codex") == "codex"
    assert normalize_agent_adapter_kind("claude-code") == "claude"
    assert normalize_agent_adapter_kind("open-code") == "opencode"
    assert legacy_normalize_agent_adapter_kind("claudecode") == "claude"

    with pytest.raises(LooporaError, match="unsupported agent adapter"):
        normalize_agent_adapter_kind("unknown-agent")


def test_agent_native_adapter_surface_exposes_host_native_contract() -> None:
    surface = agent_adapter_native_surface_summary("codex")

    assert surface["entry_kind"] == "project_skill"
    assert surface["entry_paths"]["plan"] == ".agents/skills/loopora-plan/SKILL.md"
    assert surface["entry_paths"]["run"] == ".agents/skills/loopora-run/SKILL.md"
    assert surface["role_agents"]["builder"]["target_agent"] == "loopora-builder"
    assert surface["role_agents"]["builder"]["path"] == ".codex/agents/loopora-builder.toml"
    assert surface["context_identity_env"] == ["LOOPORA_AGENT_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"]

    _assert_capability_contract(surface["capability_contract"])
    _assert_packaging_boundary(surface["packaging"])
    _assert_context_loading_boundary(surface["context_loading"])
    _assert_health_and_recovery_boundaries(surface)
    _assert_runtime_boundaries(surface)
    _assert_ownership_boundary(surface, expected_managed_hooks=[])
    _assert_dispatch_boundary(surface["native_dispatch"], expected_tools=["spawn_agent"])


def test_agent_native_run_surface_is_compact_but_keeps_dispatch_proof_boundary() -> None:
    surface = agent_adapter_native_run_surface_summary("opencode")

    assert surface["entry_kind"] == "project_command"
    assert surface["entry_paths"]["run"] == ".opencode/commands/loopora-run.md"
    assert surface["target_agents"] == [
        "loopora-builder",
        "loopora-inspector",
        "loopora-gatekeeper",
        "loopora-guide",
        "loopora-orchestrator",
    ]
    assert surface["host_mechanism"].startswith("OpenCode project command")
    assert surface["accepted_native_tools"] == ["task"]
    _assert_capability_contract(surface["capability_contract"])
    _assert_packaging_boundary(surface["packaging"])
    _assert_context_loading_boundary(surface["context_loading"])
    _assert_health_and_recovery_boundaries(surface)
    _assert_runtime_boundaries(surface)
    _assert_ownership_boundary(surface, expected_managed_hooks=[])
    assert surface["nested_provider_cli"] == "not_used"
    assert "Loopora evidence refs" in surface["proof_boundary"]
    assert agent_adapter_context_identity_env("opencode") == ["LOOPORA_AGENT_SESSION_ID", "OPENCODE_SESSION_ID"]
    assert agent_adapter_native_capability_contract("claude")["role_dispatch"] == "host_native"
    assert agent_adapter_native_capability_contract("claude")["activation"] == "explicit_loopora_command_or_cli_only"


def test_claude_native_surface_marks_only_loopora_session_context_hook_as_owned() -> None:
    surface = agent_adapter_native_surface_summary("claude")

    assert "managed_session_context_hook" in surface["ownership_boundary"]["loopora_owned"]
    _assert_ownership_boundary(surface, expected_managed_hooks=["claude_session_context_hook"])
    assert surface["health_check"]["scope"] == "managed_entries_role_configs_and_loopora_state"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"


def _assert_capability_contract(capability: dict) -> None:
    assert capability["execution_owner"] == "current_host_agent"
    assert capability["activation"] == "explicit_loopora_command_or_cli_only"
    assert capability["command_namespace"] == "loopora_plan_run_only_no_generic_host_command_aliases"
    assert capability["role_dispatch"] == "host_native"
    assert capability["workspace_owner"] == "current_host_agent_workdir"
    assert capability["worktree_management"] == "not_created_or_switched_by_loopora"
    assert capability["proof_owner"] == "loopora_evidence_refs_and_task_verdict"
    assert capability["nested_provider_cli"] == "not_used"


def _assert_packaging_boundary(packaging: dict) -> None:
    assert packaging["behavior_source"] == "loopora_core_and_managed_references"
    assert packaging["host_entries"] == "generated_thin_project_local_packaging"
    assert packaging["install_scope"] == "project_local_no_global_marketplace_or_skill_cache"
    assert packaging["entry_visibility"] == "adapter_project_entries_checked_not_global_skill_sync_assumed"
    assert packaging["runtime_bundle"] == "entries_roles_references_and_state_checked_together"
    assert packaging["update_policy"] == "explicit_check_or_init_only_no_background_auto_update"
    _assert_keys_present(
        packaging,
        {
            "projection_policy",
            "component_export",
            "shadow_policy",
            "registry_policy",
            "link_policy",
            "manifest",
            "drift_check",
            "repair",
        },
    )


def _assert_context_loading_boundary(context_loading: dict) -> None:
    assert context_loading["entry_prompt"] == "thin_dispatcher"
    assert context_loading["summary_first"] == ["agent_v3_envelope.summary"]
    assert context_loading["reference_loading"] == "on_demand_from_reference_paths"
    assert context_loading["host_memory"] == "host_owned_hint_not_binding_or_evidence"
    _assert_keys_present(
        context_loading,
        {
            "full_payload",
            "memory_store",
            "template_context",
            "workflow_kits",
            "role_catalogs",
            "compaction_context",
            "host_context",
            "catalog_context",
        },
    )


def _assert_health_and_recovery_boundaries(surface: dict) -> None:
    assert surface["health_check"]["side_effects"] == "check_commands_do_not_install_or_overwrite"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"
    assert surface["session_recovery"]["binding"] == "exact_agent_context_binding_first"
    assert surface["session_recovery"]["ambiguous"] == "list_recoverable_contexts_before_running"
    assert surface["session_recovery"]["provider_session_resume"] == "not_used_for_loopora_work"
    assert surface["session_recovery"]["host_session_discovery"] == "not_auto_discovered_or_taken_over_by_loopora"


def _assert_runtime_boundaries(surface: dict) -> None:
    handoff = surface["handoff_protocol"]
    assert handoff["role_channel"] == "host_native_role_agent"
    assert "result_template" in handoff["required_context"]
    assert handoff["payload_policy"] == "path_based_context_capsule_and_template_not_large_inline_prompt"
    assert handoff["parallel_dispatch"] == "only_when_loop_workflow_declares_parallel_group"
    assert handoff["behavioral_activation"] == "host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof"

    permission = surface["permission_boundary"]
    assert permission["policy_owner"] == "host_agent_and_user"
    assert permission["mode_switching"] == "host_agent_user_owned_not_changed_by_loopora"
    assert permission["proof_boundary"] == "approval_is_not_task_evidence"

    assert surface["tooling_boundary"]["mcp_servers"] == "host_owned_not_installed_or_enabled_by_loopora"
    assert surface["tooling_boundary"]["tool_outputs"] == "proof_only_when_submitted_as_loopora_evidence"
    assert surface["observability"]["hook_protocol"] == "adapter_specific_no_cross_host_parity_assumption"
    assert surface["observability"]["progress_signal"] == "activity_status_is_not_task_proof"
    assert surface["observability"]["proof_signal"] == "loopora_evidence_refs_and_task_verdict"


def _assert_ownership_boundary(surface: dict, *, expected_managed_hooks: list[str]) -> None:
    ownership = surface["ownership_boundary"]
    assert ownership["managed_hooks"] == expected_managed_hooks
    assert {"model_provider_defaults", "global_user_config", "user_skills_and_plugins", "mcp_servers", "permissions"}.issubset(
        set(ownership["host_owned"])
    )
    assert ownership["model_policy"] == "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof"
    assert ownership["skill_policy"] == "host_skills_plugins_not_auto_mutated_by_loopora"
    assert ownership["credential_policy"] == "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof"


def _assert_dispatch_boundary(dispatch: dict, *, expected_tools: list[str]) -> None:
    assert dispatch["orchestrator"] == "loopora-orchestrator"
    assert dispatch["accepted_native_tools"] == expected_tools
    assert dispatch["nested_provider_cli"] == "not_used"
    assert dispatch["submit_contract"] == "loopora_host_dispatch + schema-shaped result template"
    assert "Loopora evidence refs" in dispatch["proof_boundary"]


def _assert_keys_present(value: dict, keys: set[str]) -> None:
    missing = sorted(keys - set(value))

    assert not missing, f"missing expected policy keys: {missing}"
