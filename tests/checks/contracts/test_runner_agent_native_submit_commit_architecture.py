from __future__ import annotations

from runner_agent_native_architecture_support import source


def test_agent_and_headless_share_runner_step_commit_boundary() -> None:
    agent_source = source("service_agent_native.py")
    agent_claim_source = source("service_agent_native_claim.py")
    agent_submit_source = source("service_agent_native_submit.py")
    agent_submit_normalization_source = source("service_agent_native_submit_normalization.py")
    runner_source = source("service_runner_step_execution.py")
    commit_source = source("service_runner_step_commit.py")
    artifacts_source = source("service_runner_step_artifacts.py")
    step_result_source = source("engine", "step_result.py")

    agent_boundary_source = agent_source + agent_claim_source + agent_submit_source + agent_submit_normalization_source
    assert "submit_runner_step_result" in agent_boundary_source
    assert "submit_runner_step_result" in runner_source
    assert "commit_runner_step_result" not in agent_boundary_source
    assert "commit_runner_step_result" not in runner_source
    assert "def submit_runner_step_result" in commit_source
    assert "def require_runner_step_result_submittable" in commit_source
    assert "validate_step_submission(" in commit_source
    assert "class ServiceRunnerStepCommitMixin" in commit_source
    assert "class ServiceRunnerStepArtifactsMixin" in artifacts_source
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
