from __future__ import annotations

from agent_adapter_expected import (
    EXPECTED_NATIVE_CONTEXT_LOADING,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
)
from loopora.agent_native_surface import attach_native_run_surface


def test_attach_native_run_surface_uses_result_adapter_or_codex_default() -> None:
    summary: dict[str, object] = {}
    attach_native_run_surface(summary, {"adapter": "opencode"})

    surface = summary["agent_surface"]
    assert surface["entry_kind"] == "project_command"
    assert surface["entry_paths"]["plan"] == ".opencode/commands/loopora-plan.md"
    assert surface["capability_contract"]["command_namespace"] == "loopora_plan_run_only_no_generic_host_command_aliases"
    assert surface["host_mechanism"].startswith("OpenCode project command")
    assert surface["accepted_native_tools"] == ["task"]
    assert surface["packaging"] == EXPECTED_NATIVE_PACKAGING
    assert surface["context_loading"] == EXPECTED_NATIVE_CONTEXT_LOADING
    assert surface["health_check"]["install_check"] == "loopora init opencode --workdir <project> --check"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"
    assert surface["session_recovery"]["ready_resume"] == "/loopora-run option:<recoverable_context_id>"
    assert (
        surface["session_recovery"]["host_session_discovery"]
        == "not_auto_discovered_or_taken_over_by_loopora"
    )
    assert (
        surface["session_recovery"]["checkpoint_restore"]
        == "host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_context_or_proof"
    )
    _assert_native_run_surface_runtime_boundaries(surface)
    assert surface["capability_contract"]["activation"] == "explicit_loopora_command_or_cli_only"
    assert surface["capability_contract"]["workspace_owner"] == "current_host_agent_workdir"
    assert surface["capability_contract"]["worktree_management"] == "not_created_or_switched_by_loopora"
    assert surface["ownership_boundary"]["skill_policy"] == "host_skills_plugins_not_auto_mutated_by_loopora"
    assert "permissions" in surface["ownership_boundary"]["host_owned"]
    assert "credentials_and_environment_secrets" in surface["ownership_boundary"]["host_owned"]
    assert (
        surface["ownership_boundary"]["credential_policy"]
        == "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof"
    )
    assert surface["nested_provider_cli"] == "not_used"

    default_summary: dict[str, object] = {}
    attach_native_run_surface(default_summary)
    assert default_summary["agent_surface"]["entry_kind"] == "project_skill"


def _assert_native_run_surface_runtime_boundaries(surface: dict) -> None:
    assert surface["handoff_protocol"]["role_channel"] == "host_native_role_agent"
    assert surface["handoff_protocol"]["payload_policy"] == "path_based_context_step_contract_and_template_not_large_inline_prompt"
    assert surface["handoff_protocol"]["parallel_dispatch"] == "only_when_loop_workflow_declares_parallel_group"
    assert surface["handoff_protocol"]["external_orchestration"] == (
        "host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract"
    )
    assert (
        surface["handoff_protocol"]["behavioral_activation"]
        == "host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof"
    )
    assert surface["permission_boundary"] == EXPECTED_NATIVE_PERMISSION_BOUNDARY
    assert surface["tooling_boundary"] == EXPECTED_NATIVE_TOOLING_BOUNDARY
    assert surface["observability"] == EXPECTED_NATIVE_OBSERVABILITY
