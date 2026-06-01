from __future__ import annotations

from agent_adapter_test_support import (
    CliRunner,
    EXPECTED_NATIVE_CONTEXT_LOADING,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
    Path,
    _assert_loopora_cli_command,
    _assert_output_contains,
    cli,
    json,
    pytest,
)
from loopora.agent_native_result_template import agent_native_step_view_result_template


def _adapter_entry_paths_text(adapter: str) -> str:
    return {
        "codex": ".agents/skills/loopora-plan/SKILL.md and .agents/skills/loopora-run/SKILL.md",
        "claude": ".claude/skills/loopora-plan/SKILL.md and .claude/skills/loopora-run/SKILL.md",
        "opencode": ".opencode/commands/loopora-plan.md and .opencode/commands/loopora-run.md",
    }[adapter]


def _assert_native_surface_plain_output(output: str) -> None:
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


def _assert_native_surface_packaging(surface: dict) -> None:
    assert surface["packaging"] == EXPECTED_NATIVE_PACKAGING


def _assert_native_surface_context_loading(surface: dict) -> None:
    context_loading = surface["context_loading"]
    assert context_loading["summary_first"] == ["agent_v3_envelope.summary"]
    assert context_loading == EXPECTED_NATIVE_CONTEXT_LOADING


def _assert_native_surface_payload(payload: dict, *, adapter: str, entry_paths: str) -> None:
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
    _assert_native_surface_packaging(surface)
    _assert_native_surface_context_loading(surface)
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


def _assert_first_task_message_example(value: str) -> None:
    assert "Goal:" in value
    assert "Fake-done risks:" in value
    assert "Required evidence:" in value
    assert "Judgment tradeoffs:" in value


def test_agent_native_result_template_uses_schema_shaped_null_scaffold() -> None:
    template = agent_native_step_view_result_template(
        {
            "adapter": "codex",
            "run_id": "run-scaffold",
            "step_id": "builder_step",
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "native_trace_contract": {
                    "optional": True,
                    "field": "native_trace",
                    "trace_ref_field": "native_trace_ref",
                },
            },
            "native_todo": {
                "recommended": True,
                "not_evidence": True,
                "items": ["Dispatch loopora-builder through the native task tool."],
            },
            "output_schema": {
                "type": "object",
                "required": ["summary", "checks", "nested"],
                "properties": {
                    "summary": {"type": "string"},
                    "checks": {"type": "array", "items": {"type": "string"}},
                    "nested": {
                        "type": "object",
                        "required": ["status"],
                        "properties": {
                            "status": {"type": "string", "enum": ["covered", "weak"]},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "additionalProperties": False,
                    },
                    "optional_flag": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "submit_hint": {
                "command": "loopora agent codex submit --run-id run-scaffold --step-id builder_step --result-file /tmp/builder.result.json --json",
                "result_file_absolute_path": "/tmp/builder.result.json",
                "result_template_absolute_path": "/tmp/builder.result.template.json",
            },
            "judgment_contract": {
                "coverage_targets": [
                    {
                        "id": "done_when.check_001",
                        "kind": "done_when",
                        "text": "The primary user flow works end to end.",
                        "required": True,
                    },
                    {
                        "id": "success_surface.surface_001",
                        "kind": "success_surface",
                        "label": "Success surface 1",
                        "required": False,
                    },
                ]
            },
        }
    )

    assert template["loopora_result_contract"]["result_is_schema_shaped_scaffold"] is True
    assert template["loopora_result_contract"]["replace_null_placeholders_before_submit"] is True
    assert template["loopora_result_contract"]["coverage_target_ids"] == [
        "done_when.check_001",
        "success_surface.surface_001",
    ]
    assert template["loopora_result_contract"]["coverage_targets"] == [
        {
            "id": "done_when.check_001",
            "kind": "done_when",
            "required": True,
            "text": "The primary user flow works end to end.",
        },
        {
            "id": "success_surface.surface_001",
            "kind": "success_surface",
            "required": False,
            "text": "Success surface 1",
        },
    ]
    assert template["loopora_result_contract"]["result_file_to_write"] == "/tmp/builder.result.json"
    assert template["loopora_result_contract"]["submit_command"].endswith("--json")
    assert template["loopora_result_contract"]["result_template_path"] == "/tmp/builder.result.template.json"
    assert template["loopora_result_contract"]["native_todo"]["not_evidence"] is True
    assert template["loopora_result_contract"]["native_trace_contract"]["field"] == "native_trace"
    assert template["loopora_host_dispatch"]["native_trace"]["available"] is False
    assert template["loopora_host_dispatch"]["native_tool_name"] == ""
    assert template["loopora_host_dispatch"]["native_trace_ref"] == ""
    assert template["result"] == {
        "summary": None,
        "checks": [None],
        "nested": {"status": None, "notes": [None]},
        "optional_flag": None,
    }


def test_agent_native_result_template_projects_active_iteration_repair_focus() -> None:
    template = agent_native_step_view_result_template(
        {
            "adapter": "codex",
            "run_id": "run-repair",
            "step_id": "builder_step",
            "role_dispatch": {"target_agent": "loopora-builder"},
            "iteration_repair": {
                "active": True,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "status": "blocked",
                "summary": "GateKeeper rejected the pass attempt.",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence: cite supporting upstream proof."],
                "recommended_next_action": "Produce direct project-owned proof before asking GateKeeper to pass again.",
                "evidence_refs": ["ev_000_03_gatekeeper_step"],
                "top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper needs supporting evidence.",
                    }
                ],
            },
            "output_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
    )

    repair = template["loopora_result_contract"]["iteration_repair"]
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["blocking_items"][0].startswith("gatekeeper_pass_refs_not_supporting_evidence:")
    assert repair["recommended_next_action"].startswith("Produce direct project-owned proof")
    assert repair["top_gaps"][0]["target_id"] == "gatekeeper.finish"
    assert "prompt" not in template["loopora_result_contract"]


@pytest.mark.parametrize(
    ("adapter", "label"),
    [
        ("codex", "Codex"),
        ("claude", "Claude Code"),
        ("opencode", "OpenCode"),
    ],
)
def test_cli_adapter_install_human_output_points_to_agent_next_steps(tmp_path: Path, adapter: str, label: str) -> None:
    workdir = tmp_path / adapter
    workdir.mkdir()
    runner = CliRunner()
    entry_paths = _adapter_entry_paths_text(adapter)

    result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    assert f"{label} Loopora entry is installed" in result.stdout
    assert f"target project: {workdir.resolve()}" in result.stdout
    assert "next:" in result.stdout
    assert f"Return to {label} in this project" in result.stdout
    assert "task goal, fake-done risk, and required evidence" in result.stdout
    assert "/loopora-plan" in result.stdout
    assert "READY Loop preview" in result.stdout
    assert "/loopora-run" in result.stdout
    assert "same Agent session" in result.stdout
    assert "If /loopora-plan or /loopora-run is not visible" in result.stdout
    assert entry_paths in result.stdout
    assert f"refresh or restart {label}" in result.stdout
    assert "observe evidence, gaps, and verdicts" in result.stdout
    assert "first task message example:" in result.stdout
    assert "diagnostics:" in result.stdout
    assert "- verify install:" in result.stdout
    assert f"loopora init {adapter} --workdir {workdir.resolve()} --check" in result.stdout
    assert "- agent-runtime check:" in result.stdout
    assert f"loopora agent {adapter} check --workdir {workdir.resolve()}" in result.stdout
    _assert_native_surface_plain_output(result.stdout)
    if adapter == "claude":
        assert "hooks=claude_session_context_hook" in result.stdout
    else:
        assert "hooks=claude_session_context_hook" not in result.stdout
    assert "managed files:" in result.stdout
    assert result.stdout.index("next:") < result.stdout.index("managed files:")
    assert result.stdout.index("diagnostics:") < result.stdout.index("managed files:")
    assert "adapter installed" not in result.stdout
    assert "YAML bundle" not in result.stdout
    _assert_first_task_message_example(result.stdout)

    json_result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert any(f"Return to {label}" in item for item in payload["next_steps"])
    assert any("/loopora-plan" in item for item in payload["next_steps"])
    assert any("/loopora-run" in item for item in payload["next_steps"])
    assert any(entry_paths in item for item in payload["next_steps"])
    assert any(f"refresh or restart {label}" in item for item in payload["next_steps"])
    _assert_first_task_message_example(payload["first_task_message_example"])
    assert payload["next_commands"]["plan"] == "/loopora-plan"
    assert payload["next_commands"]["run"] == "/loopora-run"
    _assert_native_surface_payload(payload, adapter=adapter, entry_paths=entry_paths)
    _assert_loopora_cli_command(
        payload["next_commands"]["check"],
        f"loopora init {adapter} --workdir {workdir.resolve()} --check",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["agent_check"],
        f"loopora agent {adapter} check --workdir {workdir.resolve()}",
    )
