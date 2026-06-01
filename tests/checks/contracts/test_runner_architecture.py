from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from loopora.engine.run_requests import RunEngineClaimRunnerStepRequest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _agent_native_runtime_source() -> str:
    names = (
        "service_agent_native.py",
        "service_agent_native_claim.py",
        "service_agent_native_iteration.py",
        "service_agent_native_submit.py",
    )
    return "\n".join((REPO_ROOT / "src" / "loopora" / name).read_text(encoding="utf-8") for name in names)


def _agent_native_claim_source() -> str:
    return (REPO_ROOT / "src" / "loopora" / "service_agent_native_claim.py").read_text(encoding="utf-8")


def test_runner_support_boundary_is_runner_named() -> None:
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "runner_summary_projection.py").read_text(encoding="utf-8")
    gatekeeper_validation_source = (
        REPO_ROOT / "src" / "loopora" / "runner_gatekeeper_output_validation.py"
    ).read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_support.py").exists()
    assert "from loopora.service_runner_support import ServiceRunnerSupportMixin" in service_app_source
    assert "ServiceWorkflowSupportMixin" not in service_app_source
    assert "class ServiceRunnerSupportMixin" in support_source
    assert "from loopora.runner_summary_projection import" in support_source
    assert "def _build_runner_summary" in support_source and "return build_runner_summary(request)" in support_source
    assert "def _build_runner_iteration_entry" in support_source and "return build_runner_iteration_entry(" in support_source
    assert all(marker in summary_source for marker in ("Strategy preset", '"strategy_steps": strategy_steps'))
    assert "The loop still needs more evidence." in gatekeeper_validation_source
    assert not any(
        marker in support_source + summary_source + gatekeeper_validation_source
        for marker in ("Workflow preset", "The workflow still needs more evidence.")
    )
    assert "def build_runner_summary" in summary_source and "def build_runner_iteration_entry" in summary_source
    assert "def build_workflow_summary" not in summary_source and "def _build_workflow_summary" not in support_source
    assert "runner_summary_projection.py" in contracts_source


def test_score_history_coercion_has_shared_boundary() -> None:
    helper_source = (REPO_ROOT / "src" / "loopora" / "score_history_values.py").read_text(encoding="utf-8")
    stagnation_source = (REPO_ROOT / "src" / "loopora" / "stagnation.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "runner_summary_projection.py").read_text(encoding="utf-8")
    iteration_log_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_log_entries.py").read_text(
        encoding="utf-8"
    )
    context_summary_source = (REPO_ROOT / "src" / "loopora" / "context_iteration_summary.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "def structured_score_values" in helper_source
    assert "structured_optional_finite_number" in helper_source
    for source in (stagnation_source, summary_source, iteration_log_source, context_summary_source):
        assert "from loopora.score_history_values import" in source
        assert "def _score_values" not in source
        assert "def _number_values" not in source
    assert "score_history_values.py" in contracts_source


def test_runner_gatekeeper_output_normalization_has_dedicated_boundary() -> None:
    support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(encoding="utf-8")
    gatekeeper_output_source = (REPO_ROOT / "src" / "loopora" / "service_runner_gatekeeper_output.py").read_text(
        encoding="utf-8"
    )
    gatekeeper_validation_source = (
        REPO_ROOT / "src" / "loopora" / "runner_gatekeeper_output_validation.py"
    ).read_text(encoding="utf-8")
    gatekeeper_evidence_gate_source = (
        REPO_ROOT / "src" / "loopora" / "runner_gatekeeper_evidence_gate.py"
    ).read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_runner_gatekeeper_output import ServiceRunnerGatekeeperOutputMixin" in support_source
    assert "class ServiceRunnerGatekeeperOutputMixin" in gatekeeper_output_source
    assert "from loopora.runner_gatekeeper_output_validation import coerce_gatekeeper_output" in gatekeeper_output_source
    assert "def _coerce_gatekeeper_output" in gatekeeper_output_source
    assert "def _coerce_gatekeeper_output" not in support_source
    assert "def coerce_gatekeeper_output" in gatekeeper_validation_source
    assert all(
        marker in gatekeeper_validation_source
        for marker in (
            "gatekeeper_pass_has_unmanaged_residual_risk",
            "apply_gatekeeper_evidence_gate",
            "invalid_coverage_result_refs",
        )
    )
    assert all(
        marker in gatekeeper_evidence_gate_source
        for marker in (
            "def apply_gatekeeper_evidence_gate",
            "def build_gatekeeper_evidence_context",
            "def invalid_coverage_result_refs",
        )
    )
    assert "_apply_gatekeeper_evidence_gate" not in gatekeeper_output_source
    assert "def apply_gatekeeper_evidence_gate" not in gatekeeper_validation_source
    assert "service_runner_gatekeeper_output.py" in contracts_source
    assert "runner_gatekeeper_output_validation.py" in contracts_source
    assert "runner_gatekeeper_evidence_gate.py" in contracts_source


def test_runner_failure_boundary_is_runner_named() -> None:
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )
    failure_source = (REPO_ROOT / "src" / "loopora" / "service_runner_failure_handling.py").read_text(encoding="utf-8")

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_failure_handling.py").exists()
    assert "from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin" in runner_execution_source
    assert "ServiceWorkflowFailureHandlingMixin" not in runner_execution_source
    assert "class ServiceRunnerFailureHandlingMixin" in failure_source
    assert "def _handle_runner_exhaustion" in failure_source
    assert "def _handle_workflow_exhaustion" not in failure_source
    assert "def _handle_runner_execution_exception" in runner_execution_source
    assert "def _handle_workflow_execution_exception" not in runner_execution_source


def test_runner_execution_boundary_is_runner_named() -> None:
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )
    step_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(
        encoding="utf-8"
    )

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").exists()
    assert "from loopora.service_runner_execution import ServiceRunnerExecutionMixin" in service_app_source
    assert "ServiceWorkflowExecutionMixin" not in service_app_source
    runner_markers = (
        "class ServiceRunnerExecutionMixin",
        "ServiceRunnerStepExecutionMixin",
        "def _execute_runner_run",
        "def _run_runner_iteration",
        "def _fail_run_without_strategy_snapshot",
        "missing_strategy_snapshot",
        'phase="runner"',
    )
    step_markers = (
        "class ServiceRunnerStepExecutionMixin",
        "def _run_runner_step_once",
        "def _run_runner_iteration_steps",
        "service.runner.step.started",
    )
    workflow_markers = (
        "class ServiceWorkflowExecutionMixin",
        "def _execute_workflow_run",
        "def _run_workflow_iteration",
        "def _run_workflow_step_once",
        "_fail_run_without_workflow_snapshot",
        "missing_workflow_snapshot",
        'phase="workflow"',
        "service.workflow.",
    )
    assert all(marker in runner_execution_source for marker in runner_markers)
    assert all(marker in step_execution_source for marker in step_markers)
    assert not any(marker in runner_execution_source + step_execution_source for marker in workflow_markers)


def test_headless_runner_strategy_controls_have_dedicated_execution_boundary() -> None:
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )
    control_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_control_execution.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_runner_control_execution import ServiceRunnerControlExecutionMixin" in runner_execution_source
    assert "class ServiceRunnerControlExecutionMixin" in control_execution_source
    for marker in ("def _run_strategy_controls_for_signal", "def _run_strategy_iteration_controls"):
        assert marker in control_execution_source
        assert marker not in runner_execution_source
    assert "service_runner_control_execution.py" in contracts_source


def test_runner_context_preparation_has_dedicated_boundary() -> None:
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )
    context_preparation_source = (
        REPO_ROOT / "src" / "loopora" / "service_runner_context_preparation.py"
    ).read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_runner_context_preparation import ServiceRunnerContextPreparationMixin" in runner_execution_source
    assert "class ServiceRunnerContextPreparationMixin" in context_preparation_source
    for marker in (
        "def _prepare_runner_run_context",
        "normalize_strategy_source",
        "read_json(layout.run_contract_path)",
        "runner_started_at=time.monotonic()",
        "service.runner.execution.started",
    ):
        assert marker in context_preparation_source
        assert marker not in runner_execution_source
    assert "service_runner_context_preparation.py" in contracts_source


def test_runner_iteration_state_boundary_is_runner_named() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    progress_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_progress.py").read_text(
        encoding="utf-8"
    )
    evidence_progress_source = (REPO_ROOT / "src" / "loopora" / "runner_evidence_progress_stagnation.py").read_text(
        encoding="utf-8"
    )
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    workflow_iteration_path = REPO_ROOT / "src" / "loopora" / "service_workflow_iteration_state.py"

    assert not workflow_iteration_path.exists()
    assert "from loopora.service_runner_iteration_state import" in commit_source
    assert "from loopora.service_runner_iteration_progress import" in execution_source
    assert "class ServiceRunnerIterationProgressMixin" in progress_source
    for marker in (
        "def _new_runner_run_progress",
        "def _build_runner_iteration_state",
        "def _checkpoint_runner_iteration_progress",
    ):
        assert marker in progress_source
        assert marker not in execution_source
    assert "RunnerGatekeeperSuccessRequest" in commit_source
    assert "_finish_runner_gatekeeper_success" in commit_source
    assert "WorkflowGatekeeperSuccessRequest" not in commit_source
    assert "_finish_workflow_gatekeeper_success" not in commit_source
    assert "class ServiceRunnerIterationStateMixin" in iteration_source
    assert "from loopora.runner_evidence_progress_stagnation import" in iteration_source
    for marker in (
        "class RunnerEvidenceProgressStagnationRequest",
        "def runner_evidence_progress_stagnation",
    ):
        assert marker in evidence_progress_source
        assert marker not in iteration_source
    assert "summarize_evidence_coverage_projection" not in iteration_source
    assert "class WorkflowGatekeeperSuccessRequest" not in iteration_source
    assert "def _checkpoint_workflow_iteration_state" not in iteration_source
    assert "service_runner_iteration_progress.py" in contracts_source
    assert "runner_evidence_progress_stagnation.py" in contracts_source


def test_runner_context_and_runtime_modules_are_runner_named() -> None:
    runner_context_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_context.py").read_text(
        encoding="utf-8"
    )
    runner_runtime_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_runtime.py").read_text(
        encoding="utf-8"
    )
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )

    assert not (REPO_ROOT / "src" / "loopora" / "engine" / "workflow_context.py").exists()
    assert not (REPO_ROOT / "src" / "loopora" / "engine" / "workflow_runtime.py").exists()
    assert "class RunnerRunContext" in runner_context_source
    assert "class RunnerIterationState" in runner_context_source
    assert "strategy_source: dict" in runner_context_source
    assert "strategy_steps: list[dict]" in runner_context_source
    assert "strategy_controls: list[dict]" in runner_context_source
    assert "runner_started_at: float" in runner_context_source
    assert "workflow: dict" not in runner_context_source
    assert "workflow_steps: list[dict]" not in runner_context_source
    assert "workflow_controls: list[dict]" not in runner_context_source
    assert "workflow_started_at: float" not in runner_context_source and "context_packet" not in runner_context_source
    assert "class RunnerRunProgress" in runner_runtime_source
    assert "class RunnerStepRunRequest" in runner_runtime_source
    assert "WorkflowRunProgress" not in runner_runtime_source
    assert "WorkflowStepRunRequest" not in runner_runtime_source
    assert "from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext" in runner_runtime_source
    assert "loopora.engine.workflow_context" not in runner_runtime_source
    assert "from loopora.engine.runner_runtime import" in runner_execution_source
    assert "strategy_source: dict" in runner_execution_source
    assert "workflow: dict" not in runner_execution_source
    assert "WorkflowRunProgress" not in runner_execution_source
    assert "WorkflowStepRunRequest" not in runner_execution_source


def test_runner_step_context_inputs_have_dedicated_boundary() -> None:
    runtime_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_runtime.py").read_text(encoding="utf-8")
    instruction_context_source = (
        REPO_ROOT / "src" / "loopora" / "runner_step_instruction_contexts.py"
    ).read_text(encoding="utf-8")
    context_inputs_source = (REPO_ROOT / "src" / "loopora" / "runner_step_context_inputs.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.runner_step_instruction_contexts import prepare_runner_step_instruction_context" in runtime_source
    assert "from loopora.runner_step_context_inputs import" in instruction_context_source
    assert "def prepare_runner_step_instruction_context" in instruction_context_source
    assert "write_json(context_path, step_instruction_context)" in instruction_context_source
    assert "write_json(context_path, step_instruction_context)" not in runtime_source
    for marker in (
        "def filter_handoffs_for_step",
        "def iteration_memory_for_step",
        "def filter_evidence_for_step",
        "def merge_coverage_gap_evidence",
        "def manifest_prompt_context",
    ):
        assert marker in context_inputs_source
        assert marker not in runtime_source
    assert "runner_step_context_inputs.py" in contracts_source
    assert "runner_step_instruction_contexts.py" in contracts_source


def test_runner_role_execution_settings_have_dedicated_boundary() -> None:
    runtime_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_runtime.py").read_text(encoding="utf-8")
    settings_source = (REPO_ROOT / "src" / "loopora" / "runner_role_execution_settings.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.runner_role_execution_settings import resolve_runner_role_execution_settings" in runtime_source
    assert "def _resolve_role_execution_settings" in runtime_source
    assert "return resolve_runner_role_execution_settings(run, step, role)" in runtime_source
    for marker in (
        "def resolve_runner_role_execution_settings",
        "strategy_role_uses_execution_snapshot",
        "validate_command_args_text",
        "normalize_reasoning_effort",
    ):
        assert marker in settings_source
    assert all(marker not in runtime_source for marker in ("strategy_role_uses_execution_snapshot", "validate_command_args_text"))
    assert "runner_role_execution_settings.py" in contracts_source


def test_service_role_execution_lifecycle_has_dedicated_boundary() -> None:
    role_source = (REPO_ROOT / "src" / "loopora" / "service_role_execution.py").read_text(encoding="utf-8")
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_role_execution_lifecycle.py").read_text(
        encoding="utf-8"
    )
    legacy_requests_source = (REPO_ROOT / "src" / "loopora" / "service_legacy_role_requests.py").read_text(
        encoding="utf-8"
    )
    runtime_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_runtime.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_role_execution_lifecycle import" in role_source
    assert "from loopora.service_legacy_role_requests import" in role_source
    assert "class ServiceRoleExecutionMixin(ServiceRoleExecutionLifecycleMixin, ServiceLegacyRoleRequestMixin)" in role_source
    assert "from loopora.service_role_execution import RoleExecutionRequest" in runtime_source
    for marker in (
        "class RoleExecutionRequest",
        "def _wait_for_slot",
        "def _pause_between_iterations",
        "def _execute_role",
        "def _ensure_not_stopped",
        "def _set_mode",
    ):
        assert marker in lifecycle_source
        assert marker not in role_source
    for marker in ("def _run_check_planner", "def _run_generator", "def _run_tester", "def _execute_request"):
        assert marker in legacy_requests_source
        assert marker not in role_source
        assert marker not in lifecycle_source
    assert "class IterationRoleRunRequest" in legacy_requests_source
    assert "class IterationRoleRunRequest" not in role_source
    for marker in ("def _resolve_run_checks",):
        assert marker in role_source
        assert marker not in lifecycle_source
        assert marker not in legacy_requests_source
    assert "service_role_execution_lifecycle.py" in contracts_source
    assert "service_legacy_role_requests.py" in contracts_source


def test_runner_execution_submits_steps_through_run_engine() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")

    assert "RunEngineSubmitStepRequest" in source
    assert ".submit_step(" in source
    assert "RunEngineCommitStepRequest" not in source
    assert ".commit_step(" not in source


def test_services_use_runner_actor_factories_for_run_engine_boundaries() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    agent_source = _agent_native_runtime_source()

    assert "headless_runner_actor" in runner_source
    assert "agent_runner_actor" in agent_source
    assert 'ActorRef(kind="runner"' not in runner_source
    assert 'ActorRef(kind="agent"' not in agent_source


def test_services_use_engine_advance_policy_for_runner_step_selection() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(encoding="utf-8")
    agent_source = _agent_native_claim_source()
    runner_context_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_context.py").read_text(encoding="utf-8")
    service_sources = (runner_source, agent_source)

    assert all("runner_step_claim_plan(" in source for source in service_sources)
    assert "runner_parallel_group_claim_plan(" in runner_source
    assert "_collect_runner_parallel_group" not in runner_source
    forbidden = ("select_next_runner_step", "select_next_workflow_step", "RunnerStepSelectionRequest")
    assert all(marker not in source for source in service_sources for marker in forbidden)
    assert "def runner_step_claim_plan" in runner_context_source and "select_next_runner_step" in runner_context_source
    assert "def runner_parallel_group_claim_plan" in runner_context_source


def test_runner_parallel_group_execution_has_dedicated_boundary() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(encoding="utf-8")
    parallel_source = (REPO_ROOT / "src" / "loopora" / "service_runner_parallel_execution.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_runner_parallel_execution import" in runner_source
    assert "class ServiceRunnerStepExecutionMixin(ServiceRunnerParallelExecutionMixin)" in runner_source
    assert "class ServiceRunnerParallelExecutionMixin" in parallel_source
    for marker in (
        "def _run_runner_parallel_group",
        "ThreadPoolExecutor",
        "service.runner.parallel_group.started",
        "runner_role_error_signal",
    ):
        assert marker in parallel_source
    for marker in ("def _run_runner_parallel_group", "ThreadPoolExecutor", "service.runner.parallel_group.started"):
        assert marker not in runner_source
    assert "service_runner_parallel_execution.py" in contracts_source


def test_services_ask_run_engine_to_freeze_runner_step_instructions() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(encoding="utf-8")
    agent_source = _agent_native_claim_source()
    runner_context_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_context.py").read_text(encoding="utf-8")
    service_sources = (runner_source, agent_source)

    assert all("runner_step_claim_request(" in source for source in service_sources)
    forbidden = ("RunEngineClaimRunnerStepRequest", "RunnerStepInstructionRequest", "runner_step_instruction(", ".claim_workflow_step(")
    assert all(item not in source for source in service_sources for item in forbidden)
    assert "def runner_step_claim_request" in runner_context_source and "RunEngineClaimRunnerStepRequest(" in runner_context_source
    field_names = [field.name for field in fields(RunEngineClaimRunnerStepRequest)]
    assert field_names == ["instruction", "pending_actor", "correlation_id", "causation_id"]


def test_headless_and_agent_share_runner_step_runtime_request_boundary() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(encoding="utf-8")
    agent_source = _agent_native_claim_source()
    agent_runtime_step_source = (REPO_ROOT / "src" / "loopora" / "agent_native_claim_runtime_step.py").read_text(
        encoding="utf-8"
    )
    request_source = (REPO_ROOT / "src" / "loopora" / "runner_step_runtime_requests.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.runner_step_runtime_requests import" in runner_source
    assert "from loopora.agent_native_claim_runtime_step import" in agent_source
    assert "from loopora.runner_step_runtime_requests import" in agent_runtime_step_source
    assert "def build_runner_step_runtime_request" in request_source
    assert "class RunnerStepRuntimeInputSnapshot" in request_source
    assert "class RunnerStepRuntimeRequestBuildRequest" in request_source
    assert "structured_non_negative_int" in request_source
    for source in (runner_source, agent_runtime_step_source):
        assert "RunnerStepRuntimeRequest(" not in source
        assert "build_runner_step_runtime_request(" in source
        assert "structured_non_negative_int" not in source
    assert "runner_step_runtime_requests.py" in contracts_source


def test_agent_native_treats_active_step_state_as_projection_checked_cache() -> None:
    agent_source = _agent_native_claim_source()
    active_step_source = (REPO_ROOT / "src" / "loopora" / "agent_native_claim_active_step.py").read_text(
        encoding="utf-8"
    )
    projection_cache_source = (REPO_ROOT / "src" / "loopora" / "events" / "projection_cache.py").read_text(encoding="utf-8")
    forbidden = (".current_step_projection(", "AgentNativeCapsuleRequest", "submit_context.context_packet")
    legacy_capsule_paths = [REPO_ROOT / "src" / "loopora" / name for name in ("agent_native_capsule.py", "agent_native_capsule_context.py")]
    assert all(item in active_step_source for item in ["agent_native_active_step_is_stale", "agent_native_step_view"])
    assert all(item not in agent_source for item in forbidden)
    assert all(not path.exists() for path in legacy_capsule_paths)
    assert "refresh_agent_native_capsule_with" not in agent_source and "def _agent_native_capsule(" not in agent_source
    assert all(item in agent_source for item in ["current_step_projection_for_run", "AgentNativeStepViewRequest"])
    assert 'kind="event_replayed_current_step"' in projection_cache_source
    assert "get_projection_record(projection_name, run_id)" in projection_cache_source


def test_agent_native_writes_active_step_cache_after_run_engine_claim() -> None:
    agent_source = _agent_native_claim_source()
    claim_runtime_step = agent_source[
        agent_source.index("def _agent_native_claim_runtime_step")
        : agent_source.index("def _agent_native_step_view")
    ]

    assert claim_runtime_step.index(".claim_runner_step(") < claim_runtime_step.index(
        'state["active_step"] = agent_native_claimed_active_step_payload('
    )


def test_agent_native_uses_run_engine_runner_cursor_before_state_step_index() -> None:
    agent_source = _agent_native_claim_source()
    agent_state_source = (REPO_ROOT / "src" / "loopora" / "agent_native_state.py").read_text(encoding="utf-8")
    agent_submit_flow_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_flow.py").read_text(encoding="utf-8")
    runner_context_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_context.py").read_text(encoding="utf-8")

    assert ".runner_step_index(" not in agent_source and ".runner_step_index(" in runner_context_source
    assert ".workflow_step_index(" not in agent_source
    assert "strategy_steps=context.strategy_steps" in runner_context_source
    assert "strategy_steps=request.context.strategy_steps" in agent_submit_flow_source
    assert all(marker not in agent_source for marker in ("workflow_steps=context.strategy_steps", "workflow_steps=request.context.strategy_steps"))
    assert "strategy_steps: list[dict[str, Any]]" in agent_state_source and "workflow_steps: list[dict[str, Any]]" not in agent_state_source
    assert "fallback_step_index=coerced_non_negative_int(state.get(\"step_index\"))" in agent_source
    assert "fallback_step_index=int(state.get(\"step_index\") or 0)" not in agent_source


def test_runner_execution_submits_step_before_recording_step_evidence() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(encoding="utf-8")
    artifacts_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_artifacts.py").read_text(encoding="utf-8")
    evidence_adapter_source = (REPO_ROOT / "src" / "loopora" / "engine" / "evidence_engine_adapter.py").read_text(encoding="utf-8")

    assert "RunEngineRecordStepEvidenceRequest" in commit_source
    assert ".record_step_evidence(" in commit_source
    assert commit_source.index(".submit_step(") < commit_source.index(".record_step_evidence(")
    assert "RunEngineAcceptEvidenceRequest" not in commit_source
    assert "RunEngineCoverageRecomputedRequest" not in commit_source
    assert ".accept_evidence(" not in commit_source
    assert ".recompute_coverage(" not in commit_source
    assert "RunEngineRecordStepEvidenceRequest" not in iteration_source
    assert ".record_step_evidence(" not in iteration_source
    assert "write_runner_step_evidence_artifacts" in artifacts_source
    assert "write_evidence_coverage_projection" not in artifacts_source
    assert "write_evidence_manifest_projection" not in artifacts_source
    assert "write_evidence_coverage_projection" in evidence_adapter_source
    assert "write_evidence_manifest_projection" in evidence_adapter_source


def test_evidence_coverage_target_construction_has_dedicated_boundary() -> None:
    projection_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage.py").read_text(encoding="utf-8")
    gatekeeper_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_gatekeeper.py").read_text(encoding="utf-8")
    target_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_targets.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_summary.py").read_text(encoding="utf-8")
    target_application_source = (
        REPO_ROOT / "src" / "loopora" / "evidence_coverage_target_application.py"
    ).read_text(encoding="utf-8")
    compiler_source = (REPO_ROOT / "src" / "loopora" / "compiler" / "contract_compiler.py").read_text(encoding="utf-8")
    manifest_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest.py").read_text(encoding="utf-8")
    manifest_artifacts_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest_artifacts.py").read_text(
        encoding="utf-8"
    )
    manifest_targets_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest_targets.py").read_text(
        encoding="utf-8"
    )
    run_takeaway_evidence_source = (REPO_ROOT / "src" / "loopora" / "run_takeaway_evidence.py").read_text(encoding="utf-8")
    run_takeaway_iterations_source = (REPO_ROOT / "src" / "loopora" / "run_takeaway_iterations.py").read_text(
        encoding="utf-8"
    )
    run_takeaway_iteration_verdicts_source = (
        REPO_ROOT / "src" / "loopora" / "run_takeaway_iteration_verdicts.py"
    ).read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    for marker in ("def with_coverage_targets", "def build_coverage_targets", "def parse_target_verify_ref"):
        assert marker in target_source
        assert marker not in projection_source
    for marker in ("def latest_gatekeeper_projection", "def apply_gatekeeper_target", "def gatekeeper_has_self_measured_evidence"):
        assert marker in gatekeeper_source
        assert marker not in projection_source
    for marker in ("def summarize_evidence_coverage_projection", "def top_coverage_gaps", "def coverage_summary"):
        assert marker in summary_source
        assert marker not in projection_source
    for marker in ("def apply_target_evidence", "def coverage_result_rows", "def _target_supporting_refs"):
        assert marker in target_application_source
        assert marker not in projection_source
    assert "evidence_item_is_supporting_gatekeeper_ref" in target_application_source
    assert "evidence_item_is_supporting_gatekeeper_ref" not in projection_source
    assert "from loopora.evidence_coverage_targets import build_coverage_targets" in compiler_source
    assert "from loopora.evidence_manifest_artifacts import" in manifest_source
    assert "from loopora.evidence_manifest_targets import" in manifest_source
    for marker in ("def artifact_manifest", "def artifact_file_state", "def dedupe_artifact_refs"):
        assert marker in manifest_artifacts_source
        assert marker not in manifest_source
    for marker in ("def coverage_target_refs", "def manifest_coverage_results", "def target_index"):
        assert marker in manifest_targets_source
        assert marker not in manifest_source
    assert "from loopora.evidence_coverage_targets import parse_target_verify_ref" in manifest_targets_source
    assert "parse_target_verify_ref" not in manifest_source
    assert "from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection" in run_takeaway_evidence_source
    assert "from loopora.run_takeaway_iteration_verdicts import" in run_takeaway_iterations_source
    for marker in (
        "def terminal_task_verdict_status_for_iteration",
        "def terminal_task_verdict_summary_for_iteration",
        "ACTIVE_TAKEAWAY_RUN_STATUSES",
    ):
        assert marker in run_takeaway_iteration_verdicts_source
        assert marker not in run_takeaway_iterations_source
    assert "evidence_coverage_targets.py" in contracts_source
    assert "evidence_coverage_gatekeeper.py" in contracts_source
    assert "evidence_coverage_summary.py" in contracts_source
    assert "evidence_coverage_target_application.py" in contracts_source
    assert "evidence_manifest_artifacts.py" in contracts_source
    assert "evidence_manifest_targets.py" in contracts_source
    assert "run_takeaway_iteration_verdicts.py" in contracts_source


def test_run_finalization_uses_stable_verdict_engine_actor_factory() -> None:
    finalization_source = (REPO_ROOT / "src" / "loopora" / "service_run_finalization.py").read_text(encoding="utf-8")
    verdicts_source = (REPO_ROOT / "src" / "loopora" / "run_finalization_verdicts.py").read_text(encoding="utf-8")
    actors_source = (REPO_ROOT / "src" / "loopora" / "kernel" / "actors.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "ActorRef.verdict_engine()" in finalization_source
    assert 'ActorRef(kind="system", id="verdict-engine"' not in finalization_source
    assert "def verdict_engine" in actors_source
    assert 'id="verdict-engine"' in actors_source
    assert "from loopora.run_finalization_verdicts import" in finalization_source
    assert "def kernel_event_verdict_for_finalization" in verdicts_source
    assert "def event_verdict_for_finalization" in verdicts_source
    assert "verdict_from_legacy_coverage_projection" in verdicts_source
    assert "verdict_from_legacy_coverage_projection" not in finalization_source
    assert "run_finalization_verdicts.py" in contracts_source


def test_agent_and_headless_share_runner_step_commit_boundary() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    agent_claim_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_claim.py").read_text(encoding="utf-8")
    agent_submit_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native_submit.py").read_text(encoding="utf-8")
    agent_submit_normalization_source = (
        REPO_ROOT / "src" / "loopora" / "service_agent_native_submit_normalization.py"
    ).read_text(encoding="utf-8")
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_execution.py").read_text(encoding="utf-8")
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    artifacts_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_artifacts.py").read_text(encoding="utf-8")
    step_result_source = (REPO_ROOT / "src" / "loopora" / "engine" / "step_result.py").read_text(encoding="utf-8")

    agent_boundary_source = agent_source + agent_claim_source + agent_submit_source + agent_submit_normalization_source
    assert "submit_runner_step_result" in agent_boundary_source and "submit_runner_step_result" in runner_source
    assert "commit_runner_step_result" not in agent_boundary_source and "commit_runner_step_result" not in runner_source
    assert "def submit_runner_step_result" in commit_source and "def require_runner_step_result_submittable" in commit_source and "validate_step_submission(" in commit_source
    assert "class ServiceRunnerStepCommitMixin" in commit_source and "class ServiceRunnerStepArtifactsMixin" in artifacts_source
    assert "service.runner.step.completed" in artifacts_source
    assert "service.workflow.step.completed" not in artifacts_source
    assert "runner_step_result" in commit_source
    assert "workflow_step_result" not in commit_source
    assert "class RunnerStepResultRequest" in step_result_source
    assert "WorkflowStepResultRequest" not in step_result_source
    assert "write_runner_step_result_artifacts" in commit_source
    assert "def write_runner_step_result_artifacts" in artifacts_source
    assert "_write_runner_step_result_artifacts" not in commit_source
    assert "_commit_workflow_step_result" not in agent_boundary_source
    assert "_commit_workflow_step_result" not in runner_source
    assert "_write_workflow_step_result" not in commit_source


def test_iteration_result_enrichment_has_dedicated_boundary() -> None:
    reporting_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_reporting.py").read_text(encoding="utf-8")
    log_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_log_entries.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_summary_markdown.py").read_text(
        encoding="utf-8"
    )
    enrichment_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_result_enrichment.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_iteration_result_enrichment import" in reporting_source
    assert "from loopora.service_iteration_log_entries import" in reporting_source
    assert "from loopora.service_iteration_summary_markdown import" in reporting_source
    for marker in ("def enrich_tester_result", "def enrich_verifier_result", "def build_decision_summary"):
        assert marker in enrichment_source
        assert marker not in reporting_source
    for marker in ("def build_generator_log_entry", "def build_iteration_log_entry"):
        assert marker in log_source
        assert marker not in reporting_source + enrichment_source + summary_source
    for marker in ("def build_iteration_summary_markdown", "def format_inline_code_list", "def format_failure_refs", "def format_metric_refs"):
        assert marker in summary_source
        assert marker not in reporting_source + enrichment_source + log_source
    for marker in ("def _build_iteration_log_entry", "def _build_summary", "def _format_inline_code_list"):
        assert marker in reporting_source
        assert marker not in enrichment_source
    assert "return build_iteration_log_entry(report)" in reporting_source
    assert "return build_iteration_summary_markdown(request, truncate_text=self._truncate_text)" in reporting_source
    assert "service_iteration_result_enrichment.py" in contracts_source
    assert "service_iteration_log_entries.py" in contracts_source
    assert "service_iteration_summary_markdown.py" in contracts_source


def test_step_instruction_context_normalizers_have_dedicated_boundary() -> None:
    context_source = (REPO_ROOT / "src" / "loopora" / "context_flow.py").read_text(encoding="utf-8")
    normalizers_source = (REPO_ROOT / "src" / "loopora" / "context_step_instruction_normalizers.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.context_step_instruction_normalizers import" in context_source
    for marker in (
        "def normalize_continuation_context",
        "def normalize_evidence_coverage_summary",
        "def normalize_manifest_claims",
    ):
        assert marker in normalizers_source
        assert marker not in context_source
    assert "def build_step_instruction_context" in context_source
    assert "def build_step_instruction_context" not in normalizers_source
    assert "context_step_instruction_normalizers.py" in contracts_source
