from __future__ import annotations

# Merged from test_agent_native_cli_terminal_submit_plain.py
from agent_native_cli_terminal_submit_test_support import (
    Path,
    assert_cli_list,
    assert_codex_native_surface_plain,
    install_terminal_plain_submit_service,
    invoke_terminal_submit,
    terminal_plain_submit_fixture,
)


def test_cli_agent_submit_prints_terminal_task_verdict(monkeypatch, tmp_path: Path) -> None:
    fixture = terminal_plain_submit_fixture(tmp_path)
    layout = fixture["layout"]
    install_terminal_plain_submit_service(monkeypatch, layout)

    result = invoke_terminal_submit(fixture["workdir"], fixture["result_file"])

    assert result.exit_code == 0, result.stdout
    assert "run_status: succeeded" in result.stdout
    assert_codex_native_surface_plain(result.stdout)
    assert "submitted_step_id: gatekeeper_step" in result.stdout
    assert "submitted_status: blocked" in result.stdout
    assert_cli_list(result.stdout, "submitted_evidence_refs", "ev_000_03_gatekeeper_step")
    assert_cli_list(result.stdout, "submitted_blocking_items", "gatekeeper_pass_has_unmanaged_residual_risk")
    assert "submitted_next_action: Move the residual risk to a blocking issue or name the owner and follow-up." in result.stdout
    assert "submitted_handoff_path:" in result.stdout
    assert "03__gatekeeper_step/handoff.json" in result.stdout
    assert "submitted_summary: GateKeeper submitted terminal evidence with an insufficient-evidence verdict." in result.stdout
    assert f"run_contract_path: {layout.run_contract_path}" in result.stdout
    assert "judgment_contract_summary: Keep the evidence standard frozen through terminal submit." in result.stdout
    assert_cli_list(result.stdout, "loop_fit_reasons", "Later role outputs can drift without the frozen contract.")
    assert_cli_list(result.stdout, "judgment_tradeoffs", "Direct proof beats narrative confidence.")
    assert_cli_list(result.stdout, "execution_strategy", "Collect audit evidence before terminal closure.")
    assert_cli_list(result.stdout, "local_governance", "Inspector verifies tests/ evidence before terminal closure.")
    assert_cli_list(result.stdout, "role_postures", "GateKeeper: Separate run success from task proof.")
    assert_cli_list(result.stdout, "success_surface", "Checkout instrumentation records the buyer action.")
    assert_cli_list(result.stdout, "fake_done_states", "A story without audit evidence is fake done.")
    assert_cli_list(result.stdout, "evidence_preferences", "Audit log command output is required.")
    assert "residual_risk: Manual billing export remains a Support-owned follow-up." in result.stdout
    assert "task_verdict: insufficient_evidence" in result.stdout
    assert "task_verdict_source: gatekeeper" in result.stdout
    assert "task_verdict_summary: Required coverage still lacks direct evidence." in result.stdout
    assert "task_next_action: run lifecycle is complete but the task is not proven" in result.stdout
    assert "run /loopora-run again in this Agent session to start the next evidence pass" in result.stdout
    assert "next_loop_command: /loopora-run" in result.stdout
    assert "next_plan_action: open run_url and use Improve plan with evidence" in result.stdout
    assert "if the Loop itself needs adjustment" in result.stdout
    assert "next_evidence_focus: Required coverage still lacks direct evidence." in result.stdout
    assert "agent_runner: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_runner_task_verdict: insufficient_evidence" in result.stdout
    assert "task_proof_source: run.task_verdict" in result.stdout
    assert "run_lifecycle_source: result.complete" in result.stdout
    assert "agent_runner: complete" not in result.stdout

# Merged from test_agent_native_evidence_contract_architecture.py
from agent_native_contract_architecture_support import (
    assert_design_mentions,
    assert_markers_owned_by,
    design_contracts_source,
    loopora_source,
)


def test_agent_native_evidence_contracts_have_dedicated_boundary() -> None:
    contracts_source = loopora_source("service_agent_native_contracts.py")
    evidence_source = loopora_source("agent_native_evidence_contracts.py")
    known_refs_source = loopora_source("agent_native_known_evidence_refs.py")
    submit_validation_source = loopora_source("agent_native_submit_validation.py")
    result_template_source = loopora_source("agent_native_result_template.py")
    step_view_source = loopora_source("agent_native_step_view.py")
    refresh_source = loopora_source("agent_native_step_view_refresh.py")
    submitted_step_source = loopora_source("agent_native_submitted_step.py")

    for source in (submit_validation_source, result_template_source, submitted_step_source):
        assert "from loopora.agent_native_evidence_contracts import" in source
    for source in (step_view_source, refresh_source):
        assert "from loopora.agent_native_known_evidence_refs import" in source
    assert_markers_owned_by(
        evidence_source,
        [contracts_source],
        "def _agent_native_string_list",
        "def agent_native_unknown_evidence_refs",
        "def _agent_native_output_coverage_results",
        "AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS",
    )
    assert_markers_owned_by(
        known_refs_source,
        [evidence_source],
        "def _agent_native_compact_known_evidence_refs",
        "def _agent_native_compact_evidence_artifact_refs",
        "def _agent_native_gatekeeper_support_reason",
    )
    assert_design_mentions(design_contracts_source(), "agent_native_evidence_contracts.py", "agent_native_known_evidence_refs.py")

# Merged from test_agent_native_guidance.py
from loopora.agent_native_guidance import actionable_blocking_item
from loopora.service_agent_native_contracts import agent_native_actionable_blocking_item


def test_agent_native_blocking_summaries_explain_contract_target_tokens() -> None:
    expected = "check_001: required check id; see required_coverage.missing_check_ids and top_coverage_gaps for the contract text"

    assert actionable_blocking_item("check_001") == expected
    assert agent_native_actionable_blocking_item("check_001") == expected
    assert actionable_blocking_item("done_when.check_001").startswith("done_when.check_001: coverage target id")
    assert agent_native_actionable_blocking_item("gatekeeper.finish").startswith("gatekeeper.finish: GateKeeper finish target")

# Merged from test_agent_native_host_dispatch_literal_validation.py
from compacted_agent_native_support import (
    assert_host_dispatch_inline_literal_errors,
    assert_host_dispatch_schema_version_literal_errors,
    assert_role_dispatch_contract_literal_errors,
    assert_role_dispatch_requirement_errors,
)


def test_agent_native_host_dispatch_requires_literal_role_dispatch_booleans(service_factory) -> None:
    service = service_factory(scenario="success")

    assert_role_dispatch_requirement_errors(service)
    assert_role_dispatch_contract_literal_errors(service)
    assert_host_dispatch_inline_literal_errors(service)
    assert_host_dispatch_schema_version_literal_errors(service)

# Merged from test_agent_native_host_dispatch_native_trace.py
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    json,
)


def test_agent_native_submit_preserves_optional_official_native_trace(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_yaml = alignment_bundle_yaml(str(sample_workdir.resolve())).replace(
        "Future iterations stay anchored to this contract",
        "Preserve native subagent trace proof when the host exposes it. Future iterations stay anchored to this contract",
    )
    bundle_file.write_text(bundle_yaml, encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Preserve native subagent trace proof when the host exposes it.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    step = started["next_step"]
    dispatch = _agent_native_host_dispatch("codex", step)
    dispatch["native_tool_name"] = "spawn_agent"
    dispatch["native_trace_ref"] = "codex-tool-call-123"
    dispatch["native_trace"] = {
        "available": True,
        "tool_name": "spawn_agent",
        "tool_call_id": "toolu_codex_123",
        "subagent_run_id": "subagent-run-1",
        "event_ref": "events.jsonl#12",
    }

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_step_output(step),
            host_dispatch=dispatch,
            entry_source="codex_project_skill",
        )
    )

    native_trace = result["submitted_step"]["host_dispatch"]["native_trace"]
    assert native_trace["available"] is True
    assert native_trace["tool_name"] == "spawn_agent"
    assert native_trace["official_tool_match"] is True
    assert native_trace["trace_ref"] == "codex-tool-call-123"
    assert native_trace["tool_call_id"] == "toolu_codex_123"
    state_path = RunArtifactLayout(Path(result["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["host_dispatches"][-1]["native_trace"]["subagent_run_id"] == "subagent-run-1"

# Merged from test_agent_native_known_evidence_support_classification.py


def test_agent_native_known_evidence_refs_classify_gatekeeper_support(
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
            message="Show which evidence refs can support GateKeeper.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    proof_path = sample_workdir / "proof" / "primary-flow.txt"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text("PASS: primary flow proof is project-owned.\n", encoding="utf-8")
    builder_output = _agent_native_step_output(builder_step)
    builder_output["changed_files"] = ["proof/primary-flow.txt"]
    builder_output["proof_files"] = ["proof/primary-flow.txt"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=builder_output,
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    step_refs = {item["id"]: item for item in contract_step["known_evidence_refs"]}
    assert step_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in step_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert step_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

    template = json.loads(Path(contract_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in template_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert template_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

# Merged from test_agent_native_next_step_sections_architecture.py
from loopora.agent_native_next_step_sections import agent_dispatch_unavailable_summary



def test_agent_native_next_step_sections_have_dedicated_boundary() -> None:
    next_step_source = loopora_source("agent_native_next_step_summary.py")
    section_source = loopora_source("agent_native_next_step_sections.py")
    current_step_source = loopora_source("cli_agent_current_step_output.py")
    evidence_output_source = loopora_source("cli_agent_current_step_evidence_output.py")
    step_results_source = loopora_source("cli_agent_step_results.py")
    entry_projection_source = loopora_source("agent_entry_run_projection.py")
    design_source = design_contracts_source()

    assert "from loopora.agent_native_next_step_sections import" in next_step_source
    for source in (current_step_source, evidence_output_source, step_results_source, entry_projection_source):
        assert "from loopora.agent_native_next_step_sections import" in source
    for marker in (
        "def agent_dispatch_unavailable_summary",
        "def agent_next_step_continuation_summary",
        "def agent_current_step_evidence_scope_summary",
        "def action_policy_summary",
        "def agent_native_todo_summary",
        "def agent_iteration_repair_summary",
    ):
        assert marker in section_source
        assert marker not in next_step_source
    assert "prefix_loopora_command" in section_source
    assert "prefix_loopora_command" not in next_step_source
    dispatch_unavailable = agent_dispatch_unavailable_summary(
        adapter="codex",
        workdir="$PWD",
        role_dispatch={"target_agent": "loopora-builder", "target_agent_config_exists": False},
    )
    assert 'loopora agent codex check --workdir "$PWD"' in dispatch_unavailable["check_command"]
    assert 'loopora init codex --workdir "$PWD"' in dispatch_unavailable["repair_command"]
    assert "agent_native_next_step_sections.py" in design_source

# Merged from test_agent_native_observation_current_handoff.py
from agent_adapter_test_support import (
    _assert_agent_native_observation_artifacts,
    _assert_agent_native_observation_current_step,
)


def test_agent_native_observation_snapshot_projects_current_handoff(
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
            message="Ship the focused starter experience with evidence gaps visible.",
            bundle_file=bundle_file,
            context_id="thread-handoff",
            entry_source="codex_project_skill",
        )
    )

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-handoff",
        entry_source="codex_project_skill",
        execute_async=False,
    )
    snapshot = service.run_observation_snapshot(started["run"]["id"])

    assert started["next_step"]["known_evidence_count"] == 0
    assert started["next_step"]["known_evidence_ids"] == []
    current_step = snapshot["current_agent_step"]
    _assert_agent_native_observation_current_step(current_step)
    _assert_agent_native_observation_artifacts(service, current_step, started, sample_workdir)

# Merged from test_agent_native_parallel_groups.py
import json  # noqa: F811 - compacted test keeps source-local import binding.
from types import SimpleNamespace

from loopora.agent_native_parallel_groups import agent_native_parallel_group_snapshot
from loopora.run_artifacts import RunArtifactLayout  # noqa: F811 - compacted test keeps source-local import binding.


def test_parallel_group_snapshot_rebuilds_when_cached_numeric_identity_is_bool(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.evidence_ledger_path.parent.mkdir(parents=True)
    layout.evidence_ledger_path.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {"id": "malformed_bool_iter", "iter": True, "step_id": "peer_a"},
                {"id": "current_peer", "iter": 1, "step_id": "peer_b"},
                {"id": "builder", "iter": 1, "step_id": "builder_step"},
            ]
        ),
        encoding="utf-8",
    )
    state = {
        "parallel_group_snapshot": {
            "iter_id": True,
            "parallel_group": "inspection_pack",
            "group_start": 0,
            "group_end": 2,
            "current_outputs_by_step": {"stale": {"from": "bool-cache"}},
        }
    }
    context = SimpleNamespace(
        layout=layout,
        strategy_steps=[
            {"id": "peer_a", "role_id": "inspector_a", "parallel_group": "inspection_pack"},
            {"id": "peer_b", "role_id": "inspector_b", "parallel_group": "inspection_pack"},
        ],
        role_by_id={
            "inspector_a": {"id": "inspector_a", "archetype": "inspector"},
            "inspector_b": {"id": "inspector_b", "archetype": "inspector"},
        },
    )
    iteration = SimpleNamespace(
        iter_id=1,
        current_outputs_by_step={"builder_step": {"ok": True}, "peer_a": {"peer": True}},
        current_outputs_by_role={},
        current_outputs_by_archetype={},
        current_handoffs=[],
    )

    snapshot = agent_native_parallel_group_snapshot(
        state,
        context,
        iteration,
        0,
        "inspection_pack",
        runtime_role_key=lambda role: str(role["id"]),
    )

    assert snapshot["iter_id"] == 1
    assert snapshot["current_outputs_by_step"] == {"builder_step": {"ok": True}}
    assert [item["id"] for item in snapshot["evidence_items"]] == ["malformed_bool_iter", "builder"]

# Merged from test_agent_native_result_schema_architecture.py


def test_agent_native_result_schema_has_dedicated_boundary() -> None:
    contracts_source = loopora_source("service_agent_native_contracts.py")
    schema_source = loopora_source("agent_native_result_schema.py")
    submit_validation_source = loopora_source("agent_native_submit_validation.py")
    result_template_source = loopora_source("agent_native_result_template.py")

    assert "from loopora.agent_native_result_schema import agent_native_schema_validation_issues" in submit_validation_source
    assert "from loopora.agent_native_result_schema import agent_native_result_scaffold_from_schema" in result_template_source
    assert_markers_owned_by(
        schema_source,
        [contracts_source],
        "def agent_native_schema_validation_issues",
        "def agent_native_result_scaffold_from_schema",
        "def _agent_native_schema_object_issues",
    )
    assert_design_mentions(design_contracts_source(), "agent_native_result_schema.py")

# Merged from test_agent_native_role_dispatch.py
from loopora.agent_native_role_dispatch import (
    agent_native_role_dispatch,
    agent_native_target_agent,
    agent_native_target_agent_config_path,
    agent_native_template_role_dispatch,
    agent_native_trace_contract,
)


def test_agent_native_role_dispatch_maps_role_archetypes_to_host_agent_entries(tmp_path) -> None:
    assert agent_native_target_agent("builder") == "loopora-builder"
    assert agent_native_target_agent("gatekeeper") == "loopora-gatekeeper"
    assert agent_native_target_agent("guide") == "loopora-guide"
    assert agent_native_target_agent("inspector") == "loopora-inspector"
    assert agent_native_target_agent("custom-review") == "loopora-inspector"

    assert agent_native_target_agent_config_path("codex", "loopora-builder") == ".codex/agents/loopora-builder.toml"
    assert agent_native_target_agent_config_path("claude", "loopora-builder") == ".claude/agents/loopora-builder.md"
    assert agent_native_target_agent_config_path("opencode", "loopora-builder") == ".opencode/agents/loopora-builder.md"
    assert agent_native_target_agent_config_path("unknown", "loopora-builder") == ""
    assert agent_native_target_agent_config_path("codex", "") == ""

    dispatch = agent_native_role_dispatch(adapter="codex", role_archetype="builder", workdir_path=tmp_path)

    assert dispatch["required"] is True
    assert dispatch["dispatch_contract"] == "host_native_subagent"
    assert dispatch["target_agent"] == "loopora-builder"
    assert dispatch["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert dispatch["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert dispatch["target_agent_config_exists"] is False
    assert dispatch["target_role_archetype"] == "builder"
    assert dispatch["inline_allowed"] is False
    assert dispatch["proof_field"] == "loopora_host_dispatch"
    assert dispatch["result_field"] == "result"
    assert dispatch["accepted_dispatch_modes"] == ["host_subagent", "host_task", "host_agent"]
    assert dispatch["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert dispatch["accepted_native_tools"] == ["spawn_agent"]
    assert dispatch["native_trace_contract"] == agent_native_trace_contract()


def test_agent_native_role_dispatch_reports_config_availability(tmp_path) -> None:
    config_path = tmp_path / ".opencode" / "agents" / "loopora-gatekeeper.md"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("name: loopora-gatekeeper\n", encoding="utf-8")

    dispatch = agent_native_role_dispatch(adapter="opencode", role_archetype="gatekeeper", workdir_path=tmp_path)

    assert dispatch["target_agent"] == "loopora-gatekeeper"
    assert dispatch["target_agent_config_path"] == ".opencode/agents/loopora-gatekeeper.md"
    assert dispatch["target_agent_config_absolute_path"] == str(config_path.resolve())
    assert dispatch["target_agent_config_exists"] is True
    assert dispatch["host_mechanism"].startswith("OpenCode project command")
    assert dispatch["accepted_native_tools"] == ["task"]


def test_agent_native_template_role_dispatch_keeps_only_local_fill_guide_fields(tmp_path) -> None:
    dispatch = agent_native_role_dispatch(adapter="claude", role_archetype="guide", workdir_path=tmp_path)

    template_dispatch = agent_native_template_role_dispatch(dispatch)

    assert template_dispatch == {
        "dispatch_contract": "host_native_subagent",
        "target_agent": "loopora-guide",
        "target_role_archetype": "guide",
        "inline_allowed": False,
        "proof_field": "loopora_host_dispatch",
        "result_field": "result",
        "accepted_dispatch_modes": ["host_subagent", "host_task", "host_agent"],
        "host_mechanism": "Claude Code Agent/Task with the named Loopora role agent",
        "accepted_native_tools": ["Agent", "Task"],
    }
    assert "target_agent_config_path" not in template_dispatch
    assert "target_agent_config_absolute_path" not in template_dispatch
    assert "target_agent_config_exists" not in template_dispatch
    assert "native_trace_contract" not in template_dispatch

# Merged from test_agent_native_run_dispatch_summary.py
from agent_adapter_test_support import (
    _assert_codex_native_surface_summary,
    cli_agent_adapter_commands,
)


def test_agent_run_summary_exposes_dispatch_next_when_role_agent_is_available() -> None:
    result = {
        "run": {"id": "run_dispatch", "status": "awaiting_agent"},
        "started_new_run": True,
        "complete": False,
        "next_step": {
            "step_id": "builder_step",
            "role": {"name": "Builder"},
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_path": ".codex/agents/loopora-builder.toml",
                "target_agent_config_exists": True,
            },
        },
    }

    cli_agent_adapter_commands._attach_agent_run_summary(result)

    summary = result["agent_run_summary"]
    assert summary["dispatch_next"] == (
        "invoke loopora-builder with the next context and step contract paths below; do not perform this role inline"
    )
    assert summary["next_step"]["dispatch_next"] == summary["dispatch_next"]
    _assert_codex_native_surface_summary(summary)

# Merged from test_agent_native_runner_context_boundary.py
from service_architecture_test_support import loopora_source  # noqa: F811 - compacted test keeps source-local import binding.


def test_agent_native_uses_engine_runtime_context_not_workflow_private_types() -> None:
    source = "".join(
        map(
            loopora_source,
            (
                "service_agent_native.py",
                "service_agent_native_claim.py",
                "service_agent_native_iteration.py",
                "agent_native_claim_runtime_step.py",
            ),
        )
    )
    runner_step_runtime_source = loopora_source("runner_step_runtime.py")
    runner_run_requests_source = loopora_source("runner_run_requests.py")
    runner_support_requests_source = loopora_source("runner_support_requests.py")
    service_runner_failure_source = loopora_source("service_runner_failure_handling.py")
    service_runner_iteration_source = loopora_source("service_runner_iteration_state.py")
    service_runner_step_runtime_source = loopora_source("service_runner_step_runtime.py")
    service_runner_support_source = loopora_source("service_runner_support.py")

    assert "loopora.service_runner_execution" not in source
    assert "loopora.service_runner_failure_handling" not in source
    assert "loopora.service_runner_iteration_state" not in source
    assert "loopora.service_workflow_runtime" not in source
    assert "loopora.service_runner_step_runtime" not in source
    assert "loopora.service_runner_support" not in source
    assert "loopora.engine.workflow_runtime" not in source
    assert "loopora.engine.runner_runtime" not in source
    assert "loopora.engine.runner_context" in source
    assert "loopora.engine.workflow_context" not in source
    assert "loopora.runner_run_requests" in source
    assert "loopora.workflow_run_requests" not in source
    assert "loopora.runner_support_requests" in source
    assert "loopora.workflow_support_requests" not in source
    assert "loopora.runner_step_runtime" in source
    assert "loopora.workflow_step_runtime" not in source
    assert "_prepare_runner_step_request" not in source
    assert "prepare_runner_step_request" in source
    assert "prepare_workflow_step_request" not in source
    assert "RunnerRunContext" in source
    assert "RunnerIterationState" in source
    assert "WorkflowRunContext" not in source
    assert "WorkflowIterationState" not in source
    assert "class RunnerExhaustionRequest" in runner_run_requests_source
    assert "class RunnerIterationCheckpointRequest" in runner_run_requests_source
    assert "from loopora.runner_run_requests import RunnerExhaustionRequest" in service_runner_failure_source
    assert "from loopora.runner_run_requests import RunnerIterationCheckpointRequest" in service_runner_iteration_source
    assert "class StepOutputNormalizationRequest" in runner_support_requests_source
    assert "class RunnerSummaryRequest" in runner_support_requests_source
    assert "strategy_source: dict" in runner_support_requests_source
    assert "workflow: dict" not in runner_support_requests_source
    assert "from loopora.runner_support_requests import" in service_runner_support_source
    assert "WorkflowSummaryRequest" not in service_runner_support_source
    assert "class RunnerStepRuntimeRequest" in runner_step_runtime_source
    assert "from loopora.runner_step_runtime import RunnerStepRuntimeRequest" in service_runner_step_runtime_source
    assert "class ServiceRunnerStepRuntimeMixin" in service_runner_step_runtime_source
    assert "ServiceWorkflowRuntimeMixin" not in service_runner_step_runtime_source
    assert "WorkflowStepRuntimeRequest" not in service_runner_step_runtime_source
    assert "def prepare_runner_step_request" in service_runner_step_runtime_source
    assert "def _prepare_runner_step_request" not in service_runner_step_runtime_source

# Merged from test_agent_native_step_view_known_evidence_refresh.py
from agent_adapter_test_support import (
    AgentNativeStepClaimRequest,
    RunArtifactLayout,  # noqa: F811 - compacted test keeps source-local import binding.
    json,  # noqa: F811 - compacted test keeps source-local import binding.
)


def test_agent_native_active_step_view_refresh_persists_known_evidence_count(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = result["next_step"]
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    step_contract_path = Path(step["step_contract_absolute_path"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    step_contract_file = json.loads(step_contract_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"].pop("known_evidence_count", None)
    state["active_step"]["agent_step_view"]["evidence_rules"] = [
        {
            "id": "coverage_results.target_id_must_be_known_coverage_target",
            "severity": "hard",
            "rule": "Every coverage_results.target_id must be copied exactly from judgment_contract.coverage_targets[].id.",
        }
    ]
    step_contract_file.pop("known_evidence_count", None)
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    step_contract_path.write_text(json.dumps(step_contract_file, ensure_ascii=False), encoding="utf-8")

    refreshed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=result["run"]["id"],
            entry_source="codex_project_skill",
        )
    )

    assert refreshed["next_step"]["known_evidence_count"] == 0
    refreshed_rules = {
        str(item.get("id")): str(item.get("rule"))
        for item in list(refreshed["next_step"].get("evidence_rules") or [])
        if isinstance(item, dict)
    }
    assert "loopora_result_contract.coverage_target_ids" in refreshed_rules[
        "coverage_results.target_id_must_be_known_coverage_target"
    ]
    assert json.loads(Path(refreshed["next_step"]["agent_step_view_absolute_path"]).read_text(encoding="utf-8"))[
        "known_evidence_count"
    ] == 0
    assert json.loads(step_contract_path.read_text(encoding="utf-8"))["known_evidence_count"] == 0
    refreshed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert refreshed_state["active_step"]["agent_step_view"]["known_evidence_count"] == 0
