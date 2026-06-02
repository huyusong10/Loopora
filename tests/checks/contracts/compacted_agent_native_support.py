from __future__ import annotations

# Merged from agent_native_adapter_surface_contract_support.py
def assert_capability_contract(capability: dict) -> None:
    assert capability["execution_owner"] == "current_host_agent"
    assert capability["activation"] == "explicit_loopora_command_or_cli_only"
    assert capability["command_namespace"] == "loopora_plan_run_only_no_generic_host_command_aliases"
    assert capability["role_dispatch"] == "host_native"
    assert capability["workspace_owner"] == "current_host_agent_workdir"
    assert capability["worktree_management"] == "not_created_or_switched_by_loopora"
    assert capability["proof_owner"] == "loopora_evidence_refs_and_task_verdict"
    assert capability["nested_provider_cli"] == "not_used"


def assert_packaging_boundary(packaging: dict) -> None:
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


def assert_context_loading_boundary(context_loading: dict) -> None:
    assert context_loading["entry_prompt"] == "thin_dispatcher"
    assert context_loading["summary_first"] == ["agent_v3_envelope.summary"]
    assert context_loading["reference_loading"] == "on_demand_from_reference_paths"
    assert context_loading["host_memory"] == "host_owned_hint_not_loopora_context_or_evidence"
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


def assert_health_and_recovery_boundaries(surface: dict) -> None:
    assert surface["health_check"]["side_effects"] == "check_commands_do_not_install_or_overwrite"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"
    assert surface["session_recovery"]["context_card"] == "exact_agent_context_card_first"
    assert surface["session_recovery"]["ambiguous"] == "list_recoverable_contexts_before_running"
    assert surface["session_recovery"]["provider_session_resume"] == "not_used_for_loopora_work"
    assert surface["session_recovery"]["host_session_discovery"] == "not_auto_discovered_or_taken_over_by_loopora"


def assert_runtime_boundaries(surface: dict) -> None:
    handoff = surface["handoff_protocol"]
    assert handoff["role_channel"] == "host_native_role_agent"
    assert "result_template" in handoff["required_context"]
    assert "step_contract_path" in handoff["required_context"]
    assert handoff["payload_policy"] == "path_based_context_step_contract_and_template_not_large_inline_prompt"
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


def assert_ownership_boundary(surface: dict, *, expected_managed_hooks: list[str]) -> None:
    ownership = surface["ownership_boundary"]
    assert ownership["managed_hooks"] == expected_managed_hooks
    assert {"model_provider_defaults", "global_user_config", "user_skills_and_plugins", "mcp_servers", "permissions"}.issubset(
        set(ownership["host_owned"])
    )
    assert ownership["model_policy"] == "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof"
    assert ownership["skill_policy"] == "host_skills_plugins_not_auto_mutated_by_loopora"
    assert ownership["credential_policy"] == "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof"


def assert_dispatch_boundary(dispatch: dict, *, expected_tools: list[str]) -> None:
    assert dispatch["orchestrator"] == "loopora-orchestrator"
    assert dispatch["accepted_native_tools"] == expected_tools
    assert dispatch["nested_provider_cli"] == "not_used"
    assert dispatch["submit_contract"] == "loopora_host_dispatch + schema-shaped result template"
    assert "Loopora evidence refs" in dispatch["proof_boundary"]


def _assert_keys_present(value: dict, keys: set[str]) -> None:
    missing = sorted(keys - set(value))

    assert not missing, f"missing expected policy keys: {missing}"

# Merged from agent_native_host_dispatch_literal_test_support.py
from agent_adapter_test_support import LooporaConflictError, pytest


def base_host_dispatch_context(role_dispatch: dict | None = None) -> dict:
    selected_role_dispatch = valid_role_dispatch() if role_dispatch is None else role_dispatch
    return {
        "adapter": "codex",
        "run": {"id": "run_agent"},
        "step_id": "builder_step",
        "role": {"archetype": "builder"},
        "active": {"agent_step_view": {"role_dispatch": selected_role_dispatch}},
    }


def valid_role_dispatch(**overrides) -> dict:
    role_dispatch = {
        "required": True,
        "target_agent": "loopora-builder",
        "inline_allowed": False,
        "accepted_dispatch_modes": ["host_subagent"],
    }
    role_dispatch.update(overrides)
    return role_dispatch


def valid_host_dispatch(**overrides) -> dict:
    dispatch = {
        "schema_version": 1,
        "adapter": "codex",
        "run_id": "run_agent",
        "step_id": "builder_step",
        "target_agent": "loopora-builder",
        "actual_agent": "loopora-builder",
        "dispatch_mode": "host_subagent",
        "inline": False,
    }
    dispatch.update(overrides)
    return dispatch


def assert_role_dispatch_requirement_errors(service) -> None:
    with pytest.raises(LooporaConflictError, match="role_dispatch is required"):
        service._validate_agent_native_host_dispatch(base_host_dispatch_context({}), None)

    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(base_host_dispatch_context(), None)

    with pytest.raises(LooporaConflictError, match="requires loopora_host_dispatch"):
        service._validate_agent_native_host_dispatch(base_host_dispatch_context(), {})

    with pytest.raises(LooporaConflictError, match="required must be literal true"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(valid_role_dispatch(required="true")),
            None,
        )


def assert_role_dispatch_contract_literal_errors(service) -> None:
    with pytest.raises(LooporaConflictError, match="inline_allowed must be a literal boolean"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(valid_role_dispatch(inline_allowed="false")),
            valid_host_dispatch(),
        )

    with pytest.raises(LooporaConflictError, match="target_agent is required"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(
                {
                    "required": True,
                    "inline_allowed": False,
                    "accepted_dispatch_modes": ["host_subagent"],
                }
            ),
            valid_host_dispatch(),
        )

    with pytest.raises(LooporaConflictError, match="accepted_dispatch_modes"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(valid_role_dispatch(accepted_dispatch_modes=[])),
            valid_host_dispatch(),
        )


def assert_host_dispatch_inline_literal_errors(service) -> None:
    missing_inline_dispatch = valid_host_dispatch()
    missing_inline_dispatch.pop("inline")
    with pytest.raises(LooporaConflictError, match="inline must be a literal boolean"):
        service._validate_agent_native_host_dispatch(base_host_dispatch_context(), missing_inline_dispatch)

    with pytest.raises(LooporaConflictError, match="inline must be a literal boolean"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(),
            valid_host_dispatch(inline="false"),
        )

    with pytest.raises(LooporaConflictError, match="cannot claim inline"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(),
            valid_host_dispatch(inline=True),
        )


def assert_host_dispatch_schema_version_literal_errors(service) -> None:
    with pytest.raises(LooporaConflictError, match="schema_version must be an integer"):
        service._validate_agent_native_host_dispatch(
            base_host_dispatch_context(),
            valid_host_dispatch(schema_version="latest"),
        )

    for schema_version in (True, 1.5, "1"):
        with pytest.raises(LooporaConflictError, match="schema_version must be an integer"):
            service._validate_agent_native_host_dispatch(
                base_host_dispatch_context(),
                valid_host_dispatch(schema_version=schema_version),
            )


__all__ = [
    "assert_host_dispatch_inline_literal_errors",
    "assert_host_dispatch_schema_version_literal_errors",
    "assert_role_dispatch_contract_literal_errors",
    "assert_role_dispatch_requirement_errors",
]

# Merged from agent_native_submit_contract_support.py
from dataclasses import dataclass
from typing import Any

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _drive_agent_native_until_archetype,
    alignment_bundle_yaml,
)


@dataclass(frozen=True)
class AgentNativeSubmitRejectContext:
    service: Any
    workdir: Path
    step: dict
    raw_output_path: Path


def prepare_agent_native_submit_reject_context(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> AgentNativeSubmitRejectContext:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    inspector_result = _drive_agent_native_until_archetype(
        service,
        started,
        adapter="codex",
        workdir=sample_workdir,
        archetype="inspector",
    )
    step = inspector_result["next_step"]
    raw_output_path = RunArtifactLayout(Path(inspector_result["run"]["runs_dir"])).step_output_raw_path(
        int(step["iter"]),
        int(step["step_order"]),
        str(step["step_id"]),
    )
    return AgentNativeSubmitRejectContext(
        service=service,
        workdir=sample_workdir,
        step=step,
        raw_output_path=raw_output_path,
    )


def invalid_agent_native_submit_outputs(context: AgentNativeSubmitRejectContext) -> list[tuple[dict, str]]:
    step = context.step
    workspace_claim_output = _agent_native_step_output(step)
    workspace_claim_output["changed_files"] = ["README.md"]

    extra_field_output = _agent_native_step_output(step)
    extra_field_output["unexpected_workspace_story"] = "I also edited files."

    missing_required_output = _agent_native_step_output(step)
    missing_required_output.pop("coverage_results")

    wrong_type_output = _agent_native_step_output(step)
    wrong_type_output["execution_summary"]["total_checks"] = "one"

    invalid_enum_output = _agent_native_step_output(step)
    invalid_enum_output["check_results"][0]["status"] = "ok"

    invalid_coverage_status_output = _agent_native_step_output(step)
    invalid_coverage_status_output["coverage_results"] = [
        {
            "target_id": "done_when.check_001",
            "status": "proven",
            "evidence_refs": [],
            "note": "Proven belongs in verdict buckets or notes, not coverage_results.status.",
        }
    ]

    unknown_coverage_target_output = _agent_native_step_output(step)
    unknown_coverage_target_output["coverage_results"] = [
        {
            "target_id": "invented.target_999",
            "status": "covered",
            "evidence_refs": [],
            "note": "The host must not invent a target outside the frozen judgment contract.",
        }
    ]

    return [
        (workspace_claim_output, "read-only step cannot claim workspace artifact fields"),
        (extra_field_output, r"unexpected_workspace_story is not allowed"),
        (missing_required_output, r"coverage_results is required"),
        (wrong_type_output, r"execution_summary\.total_checks expected integer"),
        (invalid_enum_output, r"check_results\[0\]\.status must be one of"),
        (invalid_coverage_status_output, r"coverage_results\[0\]\.status must be one of"),
        (unknown_coverage_target_output, r"coverage_results_unknown_target_id: invented\.target_999"),
    ]


def assert_agent_native_submit_rejected(
    context: AgentNativeSubmitRejectContext,
    output: dict,
    expected_error: str,
) -> None:
    step = context.step
    with pytest.raises(LooporaConflictError, match=expected_error):
        context.service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=context.workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not context.raw_output_path.exists()

# Merged from agent_native_terminal_unproven_continuation_test_support.py
import json
from dataclasses import dataclass
from pathlib import Path  # noqa: F811 - compacted support keeps source-local import binding.

from agent_adapter_test_support import (
    TestClient,
    _assert_agent_run_summary_continuation,
    _assert_codex_native_surface_summary,
    _assert_terminal_recovery_choice,
    _drive_agent_native_run_to_success,
    build_app,
)

HTTP_OK = 200
TERMINAL_UNPROVEN_MESSAGE = "Keep agent-native lifecycle success separate from evidence-backed task proof."


@dataclass(frozen=True)
class TerminalUnprovenRun:
    service: Any
    started: dict[str, Any]
    final: dict[str, Any]

    @property
    def run(self) -> dict[str, Any]:
        return self.final["run"]


def complete_terminal_unproven_agent_run(
    service_factory: Any,
    tmp_path: Path,
    sample_workdir: Path,
) -> TerminalUnprovenRun:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=TERMINAL_UNPROVEN_MESSAGE,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)
    return TerminalUnprovenRun(service=service, started=started, final=final)


def assert_continue_evidence_task_next_action(final: dict[str, Any]) -> None:
    assert final["task_next_action"]["kind"] == "continue_evidence"
    assert final["task_next_action"]["task_verdict_status"] == "insufficient_evidence"
    assert final["task_next_action"]["next_loop_command"] == "/loopora-run"
    assert "Run lifecycle is complete, but the task is not proven" in final["task_next_action"]["guidance"]


def assert_agent_entry_start_continuation(service: Any, run: dict[str, Any]) -> None:
    agent_entry_start = service.agent_entry_loop_start_projection(run["loop_id"])
    assert agent_entry_start["next_loop_action"] == "start_next_run_for_unproven_verdict"
    assert agent_entry_start["continuation_summary"]["previous_run_id"] == run["id"]
    assert agent_entry_start["continuation_summary"]["previous_task_verdict"]["status"] == "insufficient_evidence"
    assert agent_entry_start["continuation_summary"]["coverage"]["missing_check_count"] > 0
    assert agent_entry_start["continuation_summary"]["next_focus"]


def assert_task_verdict_artifact_matches(run: dict[str, Any]) -> None:
    artifact = Path(run["runs_dir"]) / "evidence" / "task_verdict.json"
    assert json.loads(artifact.read_text(encoding="utf-8")) == run["task_verdict"]


def assert_terminal_unproven_recovery_choice(choice: dict[str, Any], previous_run: dict[str, Any]) -> None:
    _assert_terminal_recovery_choice(
        choice,
        expected={
            "previous_run_id": previous_run["id"],
            "action": "continue_terminal_evidence",
            "status": "terminal_unproven",
            "verdict": "insufficient_evidence",
            "hint_text": "next evidence pass",
            "label_prefix": "Continue evidence from terminal run:",
            "summary_text": "Required coverage",
        },
    )


def assert_continued_terminal_unproven_run(
    service: Any,
    started: dict[str, Any],
    continued: dict[str, Any],
    previous_run: dict[str, Any],
) -> None:
    assert previous_run["status"] == "succeeded"
    assert previous_run["task_verdict"]["status"] == "insufficient_evidence"
    assert continued["started_new_run"] is True
    assert continued["complete"] is False
    assert continued["run"]["id"] != previous_run["id"]
    assert continued["run"]["status"] == "awaiting_agent"
    assert continued["run"]["loop_id"] == previous_run["loop_id"]
    continuation_summary = _assert_agent_run_summary_continuation(
        continued["agent_run_summary"],
        previous_run_id=previous_run["id"],
        previous_task_verdict_status="insufficient_evidence",
    )
    _assert_codex_native_surface_summary(continued["agent_run_summary"])
    assert continuation_summary["next_focus"]
    assert continued["next_step"]["execution_plane"] == "agent_native"
    session = service.get_alignment_session(started["session"]["id"])
    assert session["linked_run_id"] == continued["run"]["id"]
    assert continued["binding"]["linked_run_id"] == continued["run"]["id"]
    assert service.get_run(previous_run["id"])["task_verdict"]["status"] == "insufficient_evidence"


def assert_continuation_step_artifacts(continued: dict[str, Any], previous_run: dict[str, Any]) -> None:
    step_context = json.loads(Path(continued["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))
    agent_step_view = json.loads(Path(continued["next_step"]["agent_step_view_absolute_path"]).read_text(encoding="utf-8"))
    continuation = step_context["continuation"]
    assert_terminal_unproven_continuation_payload(continuation, previous_run["id"])
    assert continuation["previous_task_verdict_path"].endswith("evidence/task_verdict.json")
    assert any(gap["target_id"] == "done_when.check_001" for gap in continuation["coverage"]["top_gaps"])
    assert agent_step_view["continuation"]["previous_run_id"] == previous_run["id"]
    assert previous_run["id"] in continued["next_step"]["prompt"]
    assert "insufficient_evidence" in continued["next_step"]["prompt"]


def assert_observation_snapshot_continuation(service: Any, continued: dict[str, Any], previous_run: dict[str, Any]) -> None:
    client = TestClient(build_app(service=service))
    snapshot_response = client.get(f"/api/runs/{continued['run']['id']}/observation-snapshot")
    assert snapshot_response.status_code == HTTP_OK
    current_step = snapshot_response.json()["current_agent_step"]
    assert_terminal_unproven_continuation_payload(current_step["continuation"], previous_run["id"])
    assert current_step["continuation"]["next_focus"]


def assert_terminal_unproven_continuation_payload(continuation: dict[str, Any], previous_run_id: str) -> None:
    assert continuation["previous_run_id"] == previous_run_id
    assert continuation["previous_task_verdict"]["status"] == "insufficient_evidence"
    assert continuation["coverage"]["missing_check_count"] > 0
    assert continuation["coverage"]["target_count"] > 0
    assert continuation["coverage"]["missing_target_count"] > 0

# Merged from agent_adapter_install_native_surface_support.py
from agent_adapter_test_support import (
    EXPECTED_NATIVE_CONTEXT_LOADING,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
    _assert_output_contains,
)


def adapter_entry_paths_text(adapter: str) -> str:
    return {
        "codex": ".agents/skills/loopora-plan/SKILL.md and .agents/skills/loopora-run/SKILL.md",
        "claude": ".claude/skills/loopora-plan/SKILL.md and .claude/skills/loopora-run/SKILL.md",
        "opencode": ".opencode/commands/loopora-plan.md and .opencode/commands/loopora-run.md",
    }[adapter]


def assert_native_surface_plain_output(output: str) -> None:
    assert "agent surface:" in output
    _assert_output_contains(
        output,
        "- entry:",
        "plan=",
        "run=",
        "/loopora-plan",
        "/loopora-run",
    )
    assert "loopora-orchestrator" in output
    assert "nested provider CLI=not_used" in output
    _assert_output_contains(
        output,
        "execution=current_host_agent",
        "role_dispatch=host_native",
        "workspace=current_host_agent_workdir",
        "worktree=not_created_or_switched_by_loopora",
        "proof=loopora_evidence_refs_and_task_verdict",
        "explicit_loopora_command_or_cli_only",
        "loopora_plan_run_only_no_generic_host_command_aliases",
        "host dispatch:",
        "accepted native tools:",
        "role configs:",
        "loopora-builder=",
        "references:",
        "loopora-run-contract.md",
    )
    _assert_output_contains(
        output,
        "packaging:",
        "entries=generated_thin_project_local_packaging",
        "scope=project_local_no_global_marketplace_or_skill_cache",
        "visibility=adapter_project_entries_checked_not_global_skill_sync_assumed",
        "bundle=entries_roles_references_and_state_checked_together",
        "update=explicit_check_or_init_only_no_background_auto_update",
    )
    _assert_output_contains(
        output,
        "context loading:",
        "entry=thin_dispatcher",
        "summary_first=",
        "references=on_demand_from_reference_paths",
        "memory=host_owned_hint_not_loopora_context_or_evidence",
        "host_context=host_loaded_skills_commands_agents_editor_context_and_ide_bridges_are_hints_not_loopora_context_contract_or_evidence",
        "health check:",
        "scope=managed_entries_role_configs_and_loopora_state",
        "session recovery:",
        "ambiguous=list_recoverable_contexts_before_running",
        "host_sessions=not_auto_discovered_or_taken_over_by_loopora",
    )
    _assert_output_contains(
        output,
        "handoff:",
        "required=role_dispatch.target_agent, context_path, step_contract_path, result_template",
        "payload=path_based_context_step_contract_and_template_not_large_inline_prompt",
        "parallel=only_when_loop_workflow_declares_parallel_group",
        "permission boundary:",
        "owner=host_agent_and_user",
        "mode=host_agent_user_owned_not_changed_by_loopora",
        "tooling boundary:",
        "mcp=host_owned_not_installed_or_enabled_by_loopora",
        "observability:",
        "hook_protocol=adapter_specific_no_cross_host_parity_assumption",
        "progress=activity_status_is_not_task_proof",
        "owned state:",
        ".loopora/",
    )
    _assert_native_surface_plain_ownership(output)
    _assert_output_contains(output, "submit contract:", "loopora_host_dispatch", "proof boundary:", "Loopora evidence refs")
    assert output.index("agent surface:") < output.index("managed files:")


def _assert_native_surface_plain_ownership(output: str) -> None:
    _assert_output_contains(
        output,
        "ownership:",
        "model_provider_defaults",
        "global_user_config",
        "user_skills_and_plugins",
        "mcp_servers",
        "permissions",
        "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof",
        "host_skills_plugins_not_auto_mutated_by_loopora",
        "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof",
    )


def assert_native_surface_payload(payload: dict, *, adapter: str, entry_paths: str) -> None:
    surface = payload["native_surface"]
    expected_tools = {
        "codex": ["spawn_agent"],
        "claude": ["Agent", "Task"],
        "opencode": ["task"],
    }[adapter]
    assert surface["slash_commands"] == {"plan": "/loopora-plan", "run": "/loopora-run"}
    assert surface["entry_paths"]["plan"] in entry_paths
    assert surface["entry_paths"]["run"] in entry_paths
    assert surface["role_agents"]["orchestrator"]["target_agent"] == "loopora-orchestrator"
    assert any(path.endswith("loopora-run-contract.md") for path in surface["reference_paths"])
    assert ".loopora/" in surface["owned_state"]
    assert surface["packaging"] == EXPECTED_NATIVE_PACKAGING
    context_loading = surface["context_loading"]
    assert context_loading["summary_first"] == ["agent_v3_envelope.summary"]
    assert context_loading == EXPECTED_NATIVE_CONTEXT_LOADING
    assert surface["health_check"]["adapter_check"] == f"loopora agent {adapter} check --workdir <project>"
    assert surface["health_check"]["side_effects"] == "check_commands_do_not_install_or_overwrite"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"
    assert surface["session_recovery"]["context_card"] == "exact_agent_context_card_first"
    assert surface["session_recovery"]["not_ready"] == "return_to_loopora_plan_or_web_review"
    assert (
        surface["session_recovery"]["host_session_discovery"]
        == "not_auto_discovered_or_taken_over_by_loopora"
    )
    assert (
        surface["session_recovery"]["checkpoint_restore"]
        == "host_checkpoints_rewinds_and_session_archives_are_recovery_hints_not_loopora_context_or_proof"
    )
    _assert_native_surface_handoff_protocol(surface)
    _assert_native_surface_runtime_boundaries(surface)
    _assert_native_surface_payload_ownership(surface, adapter=adapter)
    _assert_native_dispatch_payload(surface, expected_tools=expected_tools)


def _assert_native_surface_handoff_protocol(surface: dict) -> None:
    handoff = surface["handoff_protocol"]
    assert handoff["submit_gate"] == "filled_schema_result_with_loopora_host_dispatch"
    assert "step_contract_path" in handoff["required_context"]
    assert handoff["payload_policy"] == "path_based_context_step_contract_and_template_not_large_inline_prompt"
    assert handoff["parallel_dispatch"] == "only_when_loop_workflow_declares_parallel_group"
    assert handoff["behavioral_activation"] == "host_auto_activation_or_rule_injection_is_hint_not_dispatch_proof"
    assert handoff["external_orchestration"] == (
        "host_swarms_party_modes_and_plugin_orchestrators_are_hints_not_loopora_parallel_contract"
    )


def _assert_native_surface_runtime_boundaries(surface: dict) -> None:
    assert surface["permission_boundary"] == EXPECTED_NATIVE_PERMISSION_BOUNDARY
    assert surface["tooling_boundary"] == EXPECTED_NATIVE_TOOLING_BOUNDARY
    assert surface["observability"] == EXPECTED_NATIVE_OBSERVABILITY


def _assert_native_surface_payload_ownership(surface: dict, *, adapter: str) -> None:
    ownership = surface["ownership_boundary"]
    assert ownership["repair_policy"] == "check_then_reinstall_loopora_managed_entries_only"
    assert "permissions" in ownership["host_owned"]
    assert "user_skills_and_plugins" in ownership["host_owned"]
    assert "credentials_and_environment_secrets" in ownership["host_owned"]
    assert (
        ownership["model_policy"]
        == "external_model_routers_provider_proxies_and_model_aliases_are_host_routing_not_loopora_policy_or_task_proof"
    )
    assert ownership["skill_policy"] == "host_skills_plugins_not_auto_mutated_by_loopora"
    assert ownership["credential_policy"] == "host_credentials_env_and_secrets_not_collected_or_used_as_task_proof"
    if adapter == "claude":
        assert "managed_session_context_hook" in ownership["loopora_owned"]
        assert ownership["managed_hooks"] == ["claude_session_context_hook"]
    else:
        assert ownership["managed_hooks"] == []


def _assert_native_dispatch_payload(surface: dict, *, expected_tools: list[str]) -> None:
    assert surface["capability_contract"]["execution_owner"] == "current_host_agent"
    assert surface["capability_contract"]["activation"] == "explicit_loopora_command_or_cli_only"
    assert surface["capability_contract"]["command_namespace"] == "loopora_plan_run_only_no_generic_host_command_aliases"
    assert surface["capability_contract"]["role_dispatch"] == "host_native"
    assert surface["capability_contract"]["workspace_owner"] == "current_host_agent_workdir"
    assert surface["capability_contract"]["worktree_management"] == "not_created_or_switched_by_loopora"
    assert surface["capability_contract"]["proof_owner"] == "loopora_evidence_refs_and_task_verdict"
    assert surface["native_dispatch"]["host_mechanism"]
    assert surface["native_dispatch"]["accepted_native_tools"] == expected_tools
    assert surface["native_dispatch"]["nested_provider_cli"] == "not_used"
    assert "Loopora evidence refs" in surface["native_dispatch"]["proof_boundary"]


def assert_first_task_message_example(value: str) -> None:
    assert "Goal:" in value
    assert "Fake-done risks:" in value
    assert "Required evidence:" in value
    assert "Judgment tradeoffs:" in value
