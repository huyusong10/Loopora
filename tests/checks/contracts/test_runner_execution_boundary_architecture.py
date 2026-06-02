from __future__ import annotations

from runner_architecture_test_support import design_contracts_source, loopora_path, loopora_source


def test_runner_failure_boundary_is_runner_named() -> None:
    runner_execution_source = loopora_source("service_runner_execution.py")
    failure_source = loopora_source("service_runner_failure_handling.py")

    assert not loopora_path("service_workflow_failure_handling.py").exists()
    assert "from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin" in runner_execution_source
    assert "ServiceWorkflowFailureHandlingMixin" not in runner_execution_source
    assert "class ServiceRunnerFailureHandlingMixin" in failure_source
    assert "def _handle_runner_exhaustion" in failure_source
    assert "def _handle_workflow_exhaustion" not in failure_source
    assert "def _handle_runner_execution_exception" in runner_execution_source
    assert "def _handle_workflow_execution_exception" not in runner_execution_source


def test_runner_execution_boundary_is_runner_named() -> None:
    service_app_source = loopora_source("service_app.py")
    runner_execution_source = loopora_source("service_runner_execution.py")
    step_execution_source = loopora_source("service_runner_step_execution.py")

    assert not loopora_path("service_workflow_execution.py").exists()
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
    runner_execution_source = loopora_source("service_runner_execution.py")
    control_execution_source = loopora_source("service_runner_control_execution.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_runner_control_execution import ServiceRunnerControlExecutionMixin" in runner_execution_source
    assert "class ServiceRunnerControlExecutionMixin" in control_execution_source
    for marker in ("def _run_strategy_controls_for_signal", "def _run_strategy_iteration_controls"):
        assert marker in control_execution_source
        assert marker not in runner_execution_source
    assert "service_runner_control_execution.py" in contracts_source


def test_runner_parallel_group_execution_has_dedicated_boundary() -> None:
    runner_source = loopora_source("service_runner_step_execution.py")
    parallel_source = loopora_source("service_runner_parallel_execution.py")
    contracts_source = design_contracts_source()

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
