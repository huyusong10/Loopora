from __future__ import annotations

from context_architecture_test_support import loopora_source


def test_context_flow_delegates_iteration_summary_projection() -> None:
    from loopora import context_flow
    from loopora import context_iteration_summary

    context_flow_source = loopora_source("context_flow.py")
    context_iteration_summary_source = loopora_source("context_iteration_summary.py")
    service_runner_support_source = loopora_source("service_runner_support.py")

    assert context_flow.IterationSummaryContext is context_iteration_summary.IterationSummaryContext
    assert context_flow.build_iteration_summary is context_iteration_summary.build_iteration_summary
    assert context_flow.derive_latest_state is context_iteration_summary.derive_latest_state
    assert "class IterationSummaryContext" not in context_flow_source
    assert "def build_iteration_summary" not in context_flow_source
    assert "def derive_latest_state" not in context_flow_source
    assert "class IterationSummaryContext" in context_iteration_summary_source
    assert "def build_iteration_summary" in context_iteration_summary_source
    assert "def derive_latest_state" in context_iteration_summary_source
    assert "from loopora.context_iteration_summary import" in service_runner_support_source
