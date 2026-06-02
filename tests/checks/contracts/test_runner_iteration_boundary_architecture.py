from __future__ import annotations

from runner_architecture_test_support import design_contracts_source, loopora_path, loopora_source


def test_runner_iteration_state_boundary_is_runner_named() -> None:
    commit_source = loopora_source("service_runner_step_commit.py")
    execution_source = loopora_source("service_runner_execution.py")
    progress_source = loopora_source("service_runner_iteration_progress.py")
    evidence_progress_source = loopora_source("runner_evidence_progress_stagnation.py")
    iteration_source = loopora_source("service_runner_iteration_state.py")
    contracts_source = design_contracts_source()
    workflow_iteration_path = loopora_path("service_workflow_iteration_state.py")

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
