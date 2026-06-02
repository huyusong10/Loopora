from __future__ import annotations

from runner_architecture_test_support import design_contracts_source, loopora_path, loopora_source


def test_runner_support_boundary_is_runner_named() -> None:
    service_app_source = loopora_source("service_app.py")
    support_source = loopora_source("service_runner_support.py")
    summary_source = loopora_source("runner_summary_projection.py")
    gatekeeper_validation_source = loopora_source("runner_gatekeeper_output_validation.py")
    contracts_source = design_contracts_source()

    assert not loopora_path("service_workflow_support.py").exists()
    assert "from loopora.service_runner_support import ServiceRunnerSupportMixin" in service_app_source
    assert "ServiceWorkflowSupportMixin" not in service_app_source
    assert "class ServiceRunnerSupportMixin" in support_source
    assert "from loopora.runner_summary_projection import" in support_source
    assert "def _build_runner_summary" in support_source
    assert "return build_runner_summary(request)" in support_source
    assert "def _build_runner_iteration_entry" in support_source
    assert "return build_runner_iteration_entry(" in support_source
    assert all(marker in summary_source for marker in ("Strategy preset", '"strategy_steps": strategy_steps'))
    assert "The loop still needs more evidence." in gatekeeper_validation_source
    assert not any(
        marker in support_source + summary_source + gatekeeper_validation_source
        for marker in ("Workflow preset", "The workflow still needs more evidence.")
    )
    assert "def build_runner_summary" in summary_source
    assert "def build_runner_iteration_entry" in summary_source
    assert "def build_workflow_summary" not in summary_source
    assert "def _build_workflow_summary" not in support_source
    assert "runner_summary_projection.py" in contracts_source
