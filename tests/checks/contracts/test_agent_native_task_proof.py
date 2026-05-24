from __future__ import annotations

from agent_adapter_helpers import (
    EXPECTED_NATIVE_CONTEXT_LOADING,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
)
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_task_proof import agent_native_task_next_action, agent_task_proof_summary, with_agent_native_judgment_contract
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES


def test_agent_task_proof_summary_treats_residual_risk_pass_as_proven() -> None:
    assert frozenset({"passed", "passed_with_residual_risk"}) == PASSING_TASK_VERDICT_STATUSES

    summary = agent_task_proof_summary(
        complete=True,
        task_verdict_status="passed_with_residual_risk",
        task_verdict_summary="Residual risk is accepted and named in the task verdict.",
        task_next_action={},
    )

    assert summary == {
        "task_proven": True,
        "task_outcome": "proven",
        "lifecycle_vs_task": "run_lifecycle_complete_task_proven",
        "task_proof_source": "run.task_verdict",
        "run_lifecycle_source": "result.complete",
    }


def test_agent_native_task_next_action_routes_terminal_unproven_runs_to_new_evidence_pass() -> None:
    action = agent_native_task_next_action(
        {
            "complete": True,
            "run": {
                "run_status": "succeeded",
                "task_verdict": {
                    "status": "insufficient_evidence",
                    "summary": "Browser proof is missing.",
                },
            },
        }
    )

    assert action["kind"] == "continue_evidence"
    assert action["reason"] == "run_lifecycle_complete_task_not_proven"
    assert action["next_loop_command"] == "/loopora-run"
    assert action["task_verdict_summary"] == "Browser proof is missing."


def test_agent_native_task_next_action_stops_terminal_passed_replay() -> None:
    action = agent_native_task_next_action(
        {
            "complete": True,
            "run": {
                "status": "succeeded",
                "task_verdict_json": {
                    "status": "passed_with_residual_risk",
                    "summary": "Residual risk is named and accepted.",
                },
            },
        }
    )

    assert action["kind"] == "already_passed"
    assert action["reason"] == "task_verdict_passed"
    assert action["task_verdict_status"] == "passed_with_residual_risk"
    assert "no new evidence pass" in action["guidance"]


def test_with_agent_native_judgment_contract_attaches_task_next_action() -> None:
    result = with_agent_native_judgment_contract(
        {
            "complete": True,
            "run": {
                "status": "succeeded",
                "task_verdict_json": {"status": "failed", "summary": "Rollback proof is missing."},
            },
        }
    )

    assert "judgment_contract" in result
    assert result["task_next_action"]["kind"] == "continue_evidence"
    assert result["task_next_action"]["task_verdict_summary"] == "Rollback proof is missing."


def test_agent_task_proof_summary_distinguishes_lifecycle_complete_from_unproven_task() -> None:
    summary = agent_task_proof_summary(
        complete=True,
        task_verdict_status="insufficient_evidence",
        task_verdict_summary="Audit proof is still missing.",
        task_next_action={
            "kind": "continue_evidence",
            "next_loop_command": "/loopora-run",
        },
    )

    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_complete_task_not_proven"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_evidence_focus"] == "Audit proof is still missing."


def test_agent_task_proof_summary_allows_cli_to_compact_next_evidence_focus() -> None:
    summary = agent_task_proof_summary(
        complete=False,
        task_verdict_status="failed",
        task_verdict_summary="Line one\n\nLine two requires follow-up.",
        task_next_action={},
        normalize_next_evidence_focus=lambda value: " ".join(value.split()),
    )

    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["next_evidence_focus"] == "Line one Line two requires follow-up."


def test_attach_native_run_surface_uses_result_adapter_or_codex_default() -> None:
    summary: dict[str, object] = {}
    attach_native_run_surface(summary, {"adapter": "opencode"})

    surface = summary["native_surface"]
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
        == "host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_binding_or_proof"
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
    assert default_summary["native_surface"]["entry_kind"] == "project_skill"


def _assert_native_run_surface_runtime_boundaries(surface: dict) -> None:
    assert surface["handoff_protocol"]["role_channel"] == "host_native_role_agent"
    assert surface["handoff_protocol"]["payload_policy"] == "path_based_context_capsule_and_template_not_large_inline_prompt"
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
