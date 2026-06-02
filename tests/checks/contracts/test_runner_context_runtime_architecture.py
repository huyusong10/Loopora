from __future__ import annotations

from runner_architecture_test_support import design_contracts_source, loopora_path, loopora_source


def test_runner_context_preparation_has_dedicated_boundary() -> None:
    runner_execution_source = loopora_source("service_runner_execution.py")
    context_preparation_source = loopora_source("service_runner_context_preparation.py")
    contracts_source = design_contracts_source()

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


def test_runner_context_and_runtime_modules_are_runner_named() -> None:
    runner_context_source = loopora_source("engine", "runner_context.py")
    runner_runtime_source = loopora_source("engine", "runner_runtime.py")
    runner_execution_source = loopora_source("service_runner_execution.py")

    assert not loopora_path("engine", "workflow_context.py").exists()
    assert not loopora_path("engine", "workflow_runtime.py").exists()
    assert "class RunnerRunContext" in runner_context_source
    assert "class RunnerIterationState" in runner_context_source
    assert "strategy_source: dict" in runner_context_source
    assert "strategy_steps: list[dict]" in runner_context_source
    assert "strategy_controls: list[dict]" in runner_context_source
    assert "runner_started_at: float" in runner_context_source
    assert "workflow: dict" not in runner_context_source
    assert "workflow_steps: list[dict]" not in runner_context_source
    assert "workflow_controls: list[dict]" not in runner_context_source
    assert "workflow_started_at: float" not in runner_context_source
    assert "context_packet" not in runner_context_source
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
