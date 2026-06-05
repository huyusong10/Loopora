from __future__ import annotations

# Merged from test_agent_native_active_step_view_validation.py
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepClaimRequest,
    LooporaError,
    Path,
    RunArtifactLayout,
    alignment_bundle_yaml,
    json,
    pytest,
)

RESULT_TEMPLATE_CONTRACT_PREFIX = "result_template_contract: Result file must contain one wrapper JSON object with loopora_host_dispatch"
RESULT_TEMPLATE_FILL_PREFIX = "result_template_fill: in the main Agent session, open the template, replace null placeholders in result"


def test_agent_native_claim_rejects_corrupted_active_step_view(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Do not turn corrupted active step views into partial execution contracts.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"] = "not-a-step-view-object"
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LooporaError, match="active step contract is invalid"):
        service.claim_agent_native_step(
            AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
        )

# Merged from test_agent_native_adapter_policy_architecture.py
from agent_adapter_architecture_test_support import (
    assert_design_mentions,
    assert_markers_absent,
    assert_markers_present,
    loopora_source,
)


def test_agent_native_adapter_policy_details_have_dedicated_boundary() -> None:
    contracts_source = loopora_source("agent_native_adapter_contracts")
    policies_source = loopora_source("agent_native_adapter_policies")
    dispatch_source = loopora_source("agent_native_adapter_dispatch_policies")
    identity_source = loopora_source("agent_native_adapter_identity")
    host_mappings_source = loopora_source("agent_native_adapter_host_mappings")

    assert "from loopora.agent_native_adapter_policies import" in contracts_source
    assert "from loopora.agent_native_adapter_dispatch_policies import" in contracts_source
    assert "from loopora.agent_native_adapter_identity import" in contracts_source
    policy_markers = (
        "def agent_adapter_packaging_policy",
        "def agent_adapter_context_loading_policy",
    )
    dispatch_markers = (
        "NATIVE_SUBMIT_CONTRACT =",
        "NATIVE_RUN_ENTRY_CONTRACT_BULLETS =",
        "def agent_adapter_accepted_native_tools",
        "def agent_adapter_native_dispatch_mechanism",
    )
    host_mapping_markers = (
        "def agent_adapter_entry_paths",
        "def agent_adapter_role_agent_paths",
        "def agent_adapter_context_identity_env",
    )
    surface_markers = (
        "def agent_adapter_native_surface_summary",
        "def agent_adapter_native_run_surface_summary",
    )
    assert_markers_present(policies_source, policy_markers)
    assert_markers_absent(contracts_source, policy_markers)
    assert_markers_present(dispatch_source, dispatch_markers)
    assert_markers_absent(policies_source, dispatch_markers)
    assert_markers_absent(contracts_source, dispatch_markers)
    assert "def normalize_agent_adapter_kind" in identity_source
    assert "def normalize_agent_adapter_kind" not in policies_source
    assert "def normalize_agent_adapter_kind" not in contracts_source
    assert_markers_present(host_mappings_source, host_mapping_markers)
    assert_markers_absent(contracts_source, host_mapping_markers)
    assert_markers_present(contracts_source, surface_markers)
    assert_markers_absent(policies_source, surface_markers)
    assert_design_mentions(
        "agent_native_adapter_policies.py",
        "agent_native_adapter_dispatch_policies.py",
        "agent_native_adapter_identity.py",
        "agent_native_adapter_host_mappings.py",
    )

# Merged from test_agent_native_adapter_surface_contract.py
from loopora.agent_native_adapter_contracts import (
    agent_adapter_context_identity_env,
    agent_adapter_native_capability_contract,
    agent_adapter_native_run_surface_summary,
    agent_adapter_native_surface_summary,
)
from compacted_agent_native_support import (
    assert_capability_contract,
    assert_context_loading_boundary,
    assert_dispatch_boundary,
    assert_health_and_recovery_boundaries,
    assert_ownership_boundary,
    assert_packaging_boundary,
    assert_runtime_boundaries,
)


def test_agent_native_adapter_surface_exposes_host_native_contract() -> None:
    surface = agent_adapter_native_surface_summary("codex")

    assert surface["entry_kind"] == "project_skill"
    assert surface["entry_paths"]["plan"] == ".agents/skills/loopora-plan/SKILL.md"
    assert surface["entry_paths"]["run"] == ".agents/skills/loopora-run/SKILL.md"
    assert surface["role_agents"]["builder"]["target_agent"] == "loopora-builder"
    assert surface["role_agents"]["builder"]["path"] == ".codex/agents/loopora-builder.toml"
    assert surface["context_identity_env"] == ["LOOPORA_AGENT_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"]

    assert_capability_contract(surface["capability_contract"])
    assert_packaging_boundary(surface["packaging"])
    assert_context_loading_boundary(surface["context_loading"])
    assert_health_and_recovery_boundaries(surface)
    assert_runtime_boundaries(surface)
    assert_ownership_boundary(surface, expected_managed_hooks=[])
    assert_dispatch_boundary(surface["native_dispatch"], expected_tools=["spawn_agent"])


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
    assert_capability_contract(surface["capability_contract"])
    assert_packaging_boundary(surface["packaging"])
    assert_context_loading_boundary(surface["context_loading"])
    assert_health_and_recovery_boundaries(surface)
    assert_runtime_boundaries(surface)
    assert_ownership_boundary(surface, expected_managed_hooks=[])
    assert surface["nested_provider_cli"] == "not_used"
    assert "Loopora evidence refs" in surface["proof_boundary"]
    assert agent_adapter_context_identity_env("opencode") == ["LOOPORA_AGENT_SESSION_ID", "OPENCODE_SESSION_ID"]
    assert agent_adapter_native_capability_contract("claude")["role_dispatch"] == "host_native"
    assert agent_adapter_native_capability_contract("claude")["activation"] == "explicit_loopora_command_or_cli_only"


def test_claude_native_surface_marks_only_loopora_session_context_hook_as_owned() -> None:
    surface = agent_adapter_native_surface_summary("claude")

    assert "managed_session_context_hook" in surface["ownership_boundary"]["loopora_owned"]
    assert_ownership_boundary(surface, expected_managed_hooks=["claude_session_context_hook"])
    assert surface["health_check"]["scope"] == "managed_entries_role_configs_and_loopora_state"
    assert surface["health_check"]["host_reload"] == "restart_or_new_host_session_may_be_required_for_entry_discovery"

# Merged from test_agent_native_cli_damaged_binding_recovery.py
from agent_native_v3_helpers import assert_agent_v3_compact_envelope, assert_agent_v3_envelope
from agent_adapter_test_support import (
    CliRunner,
    agent_adapters,
    cli,
)


def test_cli_agent_run_reports_damaged_binding_recovery(service_factory, sample_workdir: Path, monkeypatch) -> None:
    service = service_factory(scenario="success")
    binding_path = agent_adapters.agent_context_binding_path("codex", sample_workdir, context_id="thread-broken")
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-broken",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_context_card"

# Merged from test_agent_native_cli_next_json_summary.py
from agent_native_cli_next_step_view_test_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    assert_agent_next_json_summary,
    invoke_agent_next_step_view,
)


def test_cli_agent_next_json_summary_reports_compact_step_contract(monkeypatch, tmp_path: Path) -> None:
    result, _layout = invoke_agent_next_step_view(monkeypatch, tmp_path, json_output=True)

    assert result.exit_code == 0, result.stdout
    assert_agent_next_json_summary(result.stdout)


def test_cli_agent_next_compact_json_omits_raw_but_keeps_handoff(monkeypatch, tmp_path: Path) -> None:
    result, _layout = invoke_agent_next_step_view(monkeypatch, tmp_path, json_output=True, compact_json_output=True)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = assert_agent_v3_compact_envelope(
        payload,
        kind="agent_next",
        summary_key="agent_next_summary",
        status="active",
    )
    assert summary["next_step"]["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    assert summary["next_step"]["submit_command"] == "loopora agent codex submit --run-id run_next"
    assert payload["technical_handoff"]["next_step_contract_path"].endswith("step_contract.json")
    assert "next_role_dispatch_message" not in payload["technical_handoff"]

# Merged from test_agent_native_cli_next_run_contract_view.py
from agent_native_cli_next_step_view_test_support import (
    assert_agent_contract_strategy_output,
    assert_agent_next_plain_work_panel,
    assert_cli_list,
)


def test_cli_agent_next_prints_run_contract_for_intermediate_step_view(monkeypatch, tmp_path: Path) -> None:
    result, layout = invoke_agent_next_step_view(monkeypatch, tmp_path)

    assert result.exit_code == 0, result.stdout
    assert_agent_next_plain_work_panel(result.stdout)
    assert "run_status: awaiting_agent" in result.stdout
    assert_agent_contract_strategy_output(result.stdout, layout)
    assert "check_count: 1" in result.stdout
    assert_cli_list(result.stdout, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    assert_cli_list(result.stdout, "loop_fit_reasons", "The next role needs the same proof bar as the first role.")
    assert_cli_list(result.stdout, "judgment_tradeoffs", "Do not trade evidence coverage for fast handoff.")
    assert_cli_list(result.stdout, "execution_strategy", "Claim the next proof gap before expanding scope.")
    assert_cli_list(result.stdout, "local_governance", "Next role checks design and tests before submitting.")
    assert_cli_list(result.stdout, "role_postures", "Inspector: Reject handoffs without evidence refs.")
    assert_cli_list(result.stdout, "success_surface", "Support can trace the refund authorization path.")
    assert_cli_list(result.stdout, "fake_done_states", "A handoff without evidence refs is fake done.")
    assert_cli_list(result.stdout, "evidence_preferences", "Use command output and audit artifacts.")
    assert "residual_risk: Only documented support handoff risk may remain." in result.stdout

# Merged from test_agent_native_cli_next_step_handoff_view.py
from agent_native_cli_next_step_view_test_support import (
    assert_cli_handoff_contract_paths,
    assert_cli_native_dispatch_contract,
)


def test_cli_agent_next_prints_next_step_handoff_view(monkeypatch, tmp_path: Path) -> None:
    result, _layout = invoke_agent_next_step_view(monkeypatch, tmp_path)

    assert result.exit_code == 0, result.stdout
    assert "next_step_id: inspector_step" in result.stdout
    assert "next_role: Inspector" in result.stdout
    assert "next_target_agent: loopora-inspector" in result.stdout
    assert "next_target_agent_config: .codex/agents/loopora-inspector.toml" in result.stdout
    assert_cli_native_dispatch_contract(result.stdout, "loopora-inspector")
    assert "next_action_policy: read_only, can_block" in result.stdout
    assert "required_coverage: weak; required checks 1 covered / 1 missing" in result.stdout
    assert "- done_when.check_001: [weak] Authorization proof is still weak." in result.stdout
    assert "next_context_path: iterations/iter_000/steps/01__inspector_step/step_instruction_context.json" in result.stdout
    assert "next_agent_step_view_path: iterations/iter_000/steps/01__inspector_step/agent_step_view.json" in result.stdout
    assert "known_evidence_count: 4" in result.stdout
    assert "known_evidence_scope: filtered by evidence_query archetypes=builder limit=12" in result.stdout
    assert "iteration_repair_source: gatekeeper_step (GateKeeper)" in result.stdout
    assert "iteration_repair_next_action: Produce direct project-owned proof" in result.stdout
    assert "before asking GateKeeper to pass again." in result.stdout
    assert "known_evidence_refs:" in result.stdout
    assert "ev_contract result=blocked support=non_supporting reason=result is blocked" in result.stdout
    assert RESULT_TEMPLATE_CONTRACT_PREFIX in result.stdout
    assert "schema-shaped result" in result.stdout
    assert "replace null placeholders before submit" in result.stdout
    assert RESULT_TEMPLATE_FILL_PREFIX in result.stdout
    assert "keep loopora_host_dispatch, then submit the filled copy" in result.stdout
    assert_cli_handoff_contract_paths(
        result.stdout,
        step_contract_fragment="iterations/iter_000/steps/01__inspector_step/step_contract.json",
        template_fragment=".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json",
        outbox_fragment=".loopora/agent_outbox/codex",
    )
    assert "submit_hint: loopora agent codex submit --run-id run_next" in result.stdout

# Merged from test_agent_native_cli_submit_repair_bad_refs.py
from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,  # noqa: F811 - compacted test keeps source-local import binding.
    LooporaConflictError,
    LooporaError,  # noqa: F811 - compacted test keeps source-local import binding.
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    _assert_bad_ref_submit_repair_payload,
    _assert_plain_bad_ref_submit_repair,
    _assert_stale_submit_repair_payload,
    _error_text,
    _invoke_codex_submit,
    _write_agent_submit_repair_fixture,
    cli,  # noqa: F811 - compacted test keeps source-local import binding.
    json,  # noqa: F811 - compacted test keeps source-local import binding.
)


def test_cli_agent_submit_repair_json_summarizes_stale_step_and_unknown_evidence(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_agent_submit_repair_fixture(tmp_path)
    workdir = fixture["workdir"]
    layout = fixture["layout"]
    active_template = fixture["active_template"]
    stale_result_file = fixture["stale_result_file"]
    bad_ref_file = fixture["bad_ref_file"]

    class FakeService:
        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            if request.step_id == "builder_step":
                raise LooporaConflictError("submitted step_id does not match the claimed agent-native step")
            raise LooporaError("agent-native evidence_refs_unknown: invented_ev")

        def get_run(self, run_id: str):
            assert run_id == "run_submit_repair"
            return {"id": "run_submit_repair", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    stale = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="builder_step",
        result_file=stale_result_file,
    )

    assert stale.exit_code == 1
    assert _error_text(stale) == ""
    _assert_stale_submit_repair_payload(json.loads(stale.stdout), active_template=active_template)

    bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
    )

    assert bad_ref.exit_code == 1
    assert _error_text(bad_ref) == ""
    _assert_bad_ref_submit_repair_payload(json.loads(bad_ref.stdout))

    plain_bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
        json_output=False,
    )

    plain_error = _error_text(plain_bad_ref)
    assert plain_bad_ref.exit_code == 1
    _assert_plain_bad_ref_submit_repair(plain_error)

# Merged from test_agent_native_cli_submit_repair_core_dispatch.py
from agent_native_cli_submit_repair_core_blockers_test_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    install_core_blocker_service,
    invoke_core_blocker_submit,
    submit_repair_summary,
    write_core_blocker_fixture,
    write_core_blocker_result_files,
)


def test_cli_agent_submit_repair_preserves_dispatch_mismatch_blocker(monkeypatch, tmp_path: Path) -> None:
    fixture = write_core_blocker_fixture(tmp_path)
    files = write_core_blocker_result_files(fixture)
    captured_requests = install_core_blocker_service(monkeypatch, fixture)

    result = invoke_core_blocker_submit(fixture, files["mismatch"], json_output=True)

    assert result.exit_code == 1
    summary = submit_repair_summary(result)
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["submitted_dispatch"]["actual_agent"] == "loopora-gatekeeper"
    assert "auto_repair_applied" not in summary
    assert "auto_repair_attempted" not in summary
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-gatekeeper"

# Merged from test_agent_native_cli_submit_repair_core_evidence_refs.py
from agent_native_cli_submit_repair_core_blockers_test_support import (
    error_text,
)


def test_cli_agent_submit_repair_preserves_unknown_evidence_refs_blocker(monkeypatch, tmp_path: Path) -> None:
    fixture = write_core_blocker_fixture(tmp_path)
    files = write_core_blocker_result_files(fixture)
    captured_requests = install_core_blocker_service(monkeypatch, fixture)

    result = invoke_core_blocker_submit(fixture, files["evidence"], json_output=True)

    assert result.exit_code == 1
    summary = submit_repair_summary(result)
    assert summary["submit_repair"] == "repair_result_json"
    assert "use only known_evidence_ids in evidence_refs: ev_known" in summary["repair_focus"]
    assert "auto_repair_applied" not in summary
    assert summary["auto_repair_attempted"] is True
    assert summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert summary["core_blocker_preserved"] is True
    assert summary["core_blocker_kind"] == "evidence_refs_unknown"
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-builder"


def test_cli_agent_submit_repair_plain_orders_auto_repair_before_focus(monkeypatch, tmp_path: Path) -> None:
    fixture = write_core_blocker_fixture(tmp_path)
    files = write_core_blocker_result_files(fixture)
    install_core_blocker_service(monkeypatch, fixture)

    result = invoke_core_blocker_submit(fixture, files["evidence"], json_output=False)

    plain_error = error_text(result)
    assert result.exit_code == 1
    assert "auto_repair: submitted result format repaired before submit" in plain_error
    assert "Core still blocked evidence_refs_unknown" in plain_error
    assert plain_error.index("auto_repair:") < plain_error.index("repair_focus:")

# Merged from test_agent_native_cli_submit_repair_core_schema.py


def test_cli_agent_submit_repair_preserves_schema_mismatch_blocker(monkeypatch, tmp_path: Path) -> None:
    fixture = write_core_blocker_fixture(tmp_path)
    files = write_core_blocker_result_files(fixture)
    captured_requests = install_core_blocker_service(monkeypatch, fixture)

    result = invoke_core_blocker_submit(fixture, files["schema"], json_output=True)

    assert result.exit_code == 1
    summary = submit_repair_summary(result)
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["core_blocker_kind"] == "schema_mismatch"
    assert summary["auto_repair_actions"] == ["wrapped_schema_result_with_active_template_dispatch"]
    assert captured_requests[0].host_dispatch["actual_agent"] == "loopora-builder"

# Merged from test_agent_native_cli_submit_repair_schema_guidance_json.py
from agent_native_cli_submit_repair_core_blockers_test_support import (
    install_schema_repair_guidance_service,
    invoke_schema_repair_guidance_submit,
    write_schema_repair_guidance_fixture,
)


def test_cli_agent_submit_schema_error_json_reports_result_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    fixture = write_schema_repair_guidance_fixture(tmp_path)
    install_schema_repair_guidance_service(monkeypatch, fixture)

    result = invoke_schema_repair_guidance_submit(fixture, json_output=True)

    assert result.exit_code == 1
    assert error_text(result) == ""
    summary = submit_repair_summary(result)
    assert summary["ready"] is False
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["result_file_to_repair"] == str(fixture["result_file"])
    assert summary["active_step_id"] == "gatekeeper_step"
    assert summary["active_role"] == "GateKeeper"
    assert summary["active_target_agent"] == "loopora-gatekeeper"
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in summary["repair_focus"]
    assert summary["schema_lookup"].endswith("--run-id run_schema --json --compact-json --entry-source codex_project_skill")

# Merged from test_agent_native_cli_submit_repair_schema_guidance_plain.py
from agent_native_cli_submit_repair_core_blockers_test_support import (
    assert_labeled_loopora_agent_command,
)


def test_cli_agent_submit_schema_error_plain_prints_result_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    fixture = write_schema_repair_guidance_fixture(tmp_path)
    install_schema_repair_guidance_service(monkeypatch, fixture)

    result = invoke_schema_repair_guidance_submit(fixture, json_output=False)

    output = error_text(result)
    assert result.exit_code == 1
    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in output
    assert f"result_file_to_repair: {fixture['result_file']}" in output
    assert "active_step_id: gatekeeper_step" in output
    assert "active_role: GateKeeper" in output
    assert "active_target_agent: loopora-gatekeeper" in output
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in output
    schema_lookup = assert_labeled_loopora_agent_command(output, "schema_lookup", "next")
    assert f"--workdir {fixture['workdir'].resolve()}" in schema_lookup
    assert "--run-id run_schema" in schema_lookup
    assert "Traceback" not in output

# Merged from test_agent_native_cli_submit_repair_workflow_errors.py
from agent_native_cli_test_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    WorkflowError,
)


def test_cli_agent_submit_reports_workflow_errors_without_traceback(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_test",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "unreachable"},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise WorkflowError("workflow control max_fires_per_run must be between 1 and 20")

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_corrupt",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    assert "max_fires_per_run" in _error_text(result)
    assert "Traceback" not in _error_text(result)

# Merged from test_agent_native_cli_submit_schema_repairs.py
from agent_native_cli_submit_schema_repair_assertions import (
    assert_json_unfilled_template_repair,
    assert_plain_unfilled_template_repair,
)
from agent_native_cli_submit_schema_repair_fixture_support import (
    install_unfilled_template_fake_service,
    invoke_unfilled_template_submit,
    write_unfilled_template_fixture,
)


def test_cli_agent_submit_unfilled_template_reports_multiple_schema_repairs(monkeypatch, tmp_path: Path) -> None:
    fixture = write_unfilled_template_fixture(tmp_path)
    install_unfilled_template_fake_service(monkeypatch, fixture)
    runner = CliRunner()

    plain = invoke_unfilled_template_submit(runner, fixture)
    assert_plain_unfilled_template_repair(plain, fixture)

    result = invoke_unfilled_template_submit(runner, fixture, json_mode=True)
    assert_json_unfilled_template_repair(result, fixture)

# Merged from test_agent_native_cli_terminal_submit_json.py
from agent_native_cli_terminal_submit_test_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    assert_codex_native_surface_summary,
    install_terminal_json_submit_service,
    invoke_terminal_submit,
    terminal_json_submit_fixture,
    terminal_submit_summary,
)


def test_cli_agent_submit_json_preserves_terminal_task_next_action(monkeypatch, tmp_path: Path) -> None:
    fixture = terminal_json_submit_fixture(tmp_path)
    install_terminal_json_submit_service(monkeypatch, fixture["workdir"])

    result = invoke_terminal_submit(fixture["workdir"], fixture["result_file"], json_output=True)

    assert result.exit_code == 0, result.stdout
    summary = terminal_submit_summary(result.stdout)
    assert summary["run_id"] == "run_terminal"
    assert summary["run_status"] == "succeeded"
    assert summary["complete"] is True
    assert summary["submitted_step"]["step_id"] == "gatekeeper_step"
    assert summary["submitted_step"]["status"] == "passed"
    assert summary["submitted_step"]["evidence_refs"] == ["ev_000_03_gatekeeper_step"]
    assert summary["submitted_step"]["blocking_items"] == ["missing_direct_terminal_proof"]
    assert "recommended_next_action" not in summary["submitted_step"]
    assert summary["submitted_step"]["handoff_path"].endswith("run_terminal/handoff.json")
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_complete_task_not_proven"
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_plan_action"] == "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
    assert summary["next_evidence_focus"] == "Required coverage still lacks direct evidence."
    assert summary["task_next_action"]["kind"] == "continue_evidence"
    assert_codex_native_surface_summary(summary)
    assert summary["task_next_action"]["next_loop_command"] == "/loopora-run"
