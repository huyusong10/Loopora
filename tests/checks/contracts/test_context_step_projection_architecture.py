from __future__ import annotations

from context_architecture_test_support import design_contracts_source, loopora_source


def test_context_step_artifact_refs_have_dedicated_boundary() -> None:
    step_results_source = loopora_source("context_step_results.py")
    handoffs_source = loopora_source("context_step_handoffs.py")
    artifact_refs_source = loopora_source("context_step_artifact_refs.py")
    design_source = design_contracts_source()

    assert "from loopora.context_step_handoffs import" in step_results_source
    assert "from loopora.context_step_artifact_refs import" in handoffs_source
    assert "def output_workspace_artifact_refs" in artifact_refs_source
    assert "def workspace_artifact_ref" in artifact_refs_source
    assert "def _output_workspace_artifact_refs" not in step_results_source
    assert "def _workspace_artifact_ref" not in step_results_source
    assert "context_step_artifact_refs.py" in design_source


def test_context_step_result_projections_have_dedicated_boundaries() -> None:
    step_results_source = loopora_source("context_step_results.py")
    handoffs_source = loopora_source("context_step_handoffs.py")
    evidence_source = loopora_source("context_step_evidence_entries.py")
    design_source = design_contracts_source()

    assert "class StepResultContext" in step_results_source
    assert "class StepEvidenceEntryRequest" in step_results_source
    assert "def build_step_handoff" in step_results_source
    assert "return _build_step_handoff(result)" in step_results_source
    assert "def build_step_evidence_entry" in step_results_source
    assert "return _build_step_evidence_entry(request)" in step_results_source
    assert "def build_step_handoff" in handoffs_source
    assert "def build_step_evidence_entry" in evidence_source
    assert "def evidence_entry_id" in evidence_source
    assert "def _evidence_verifies" in evidence_source
    assert "def _evidence_verifies" not in step_results_source
    assert "def _handoff_core" in handoffs_source
    assert "def _handoff_core" not in step_results_source
    assert "context_step_handoffs.py" in design_source
    assert "context_step_evidence_entries.py" in design_source


def test_context_flow_delegates_run_contract_and_step_result_projections() -> None:
    from loopora import context_contract_snapshot
    from loopora import context_flow
    from loopora import context_step_results

    context_contract_snapshot_source = loopora_source("context_contract_snapshot.py")
    context_flow_source = loopora_source("context_flow.py")
    context_step_results_source = loopora_source("context_step_results.py")
    service_runner_step_artifacts_source = loopora_source("service_runner_step_artifacts.py")

    assert context_flow.RunContractSnapshotRequest is context_contract_snapshot.RunContractSnapshotRequest
    assert context_flow.build_run_contract_snapshot is context_contract_snapshot.build_run_contract_snapshot
    assert context_flow.StepResultContext is context_step_results.StepResultContext
    assert context_flow.build_step_handoff is context_step_results.build_step_handoff
    assert context_flow.evidence_entry_id is context_step_results.evidence_entry_id
    assert "class RunContractSnapshotRequest" not in context_flow_source
    assert "class RunContractSnapshotRequest" in context_contract_snapshot_source
    assert "class StepResultContext" not in context_flow_source
    assert "def build_step_handoff" not in context_flow_source
    assert "def evidence_entry_id" not in context_flow_source
    assert "class StepResultContext" in context_step_results_source
    assert "def build_step_handoff" in context_step_results_source
    assert "def evidence_entry_id" in context_step_results_source
    assert "from loopora.context_step_results import" in service_runner_step_artifacts_source
