from __future__ import annotations

from context_architecture_test_support import loopora_source


def test_run_contract_snapshot_request_uses_strategy_source_input() -> None:
    context_contract_snapshot_source = loopora_source("context_contract_snapshot.py")
    context_flow_source = loopora_source("context_flow.py")
    registration_source = loopora_source("service_run_registration.py")
    service_run_start_source = loopora_source("service_run_start.py")

    assert "class RunContractSnapshotRequest" in context_contract_snapshot_source
    assert "strategy_source: dict" in context_contract_snapshot_source
    assert "    workflow: dict\n    prompt_files" not in context_contract_snapshot_source
    assert "_strategy_source_roles_with_prompt_files" in context_contract_snapshot_source
    assert "_strategy_source_roles_with_prompt_files" not in context_flow_source
    assert "_workflow_roles_with_prompt_files" not in context_contract_snapshot_source
    assert 'strategy_snapshot = run_contract.get("workflow")' in context_flow_source
    assert 'workflow_snapshot = run_contract.get("workflow")' not in context_flow_source
    assert "StepContextPacket" not in context_flow_source
    assert "strategy_source=strategy_source" in context_contract_snapshot_source
    assert "strategy_source=strategy_snapshot" in context_flow_source
    assert "workflow=strategy_source" not in context_contract_snapshot_source
    assert "workflow=strategy_snapshot" not in context_flow_source
    assert "from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot" in service_run_start_source
    assert "class LoopCreateRequest" in loopora_source("service_loop_create_inputs.py")
    assert "class ResolvedLoopCreate" in registration_source
    assert "class LoopCreateRequest" not in registration_source
    assert "class LoopDefinitionFiles" in registration_source
    assert "strategy_source: dict" in registration_source
    assert "workflow: dict\n\n\n@dataclass(frozen=True, kw_only=True)\nclass ResolvedLoopCreate" not in registration_source
    assert "workflow: dict\n\n\ndef _coerce_loop_create_request" not in registration_source
    assert "_validate_loop_completion_strategy_source" in registration_source
    assert "def start_run" not in registration_source
    assert "def start_run" in service_run_start_source
    assert "_validate_loop_completion_workflow" not in registration_source
    assert "strategy_source = self._normalized_strategy_source_from_record(loop)" in service_run_start_source
    assert 'workflow = loop.get("workflow_json")' not in registration_source + service_run_start_source
