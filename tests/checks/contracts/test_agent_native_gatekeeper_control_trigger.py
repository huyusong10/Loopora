from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    _agent_native_host_dispatch,
    _agent_native_rejected_gatekeeper_output,
    _agent_native_step_output,
    _alignment_bundle_yaml_with_gatekeeper_control,
    _drive_agent_native_until_archetype,
    read_jsonl,
)


def test_agent_native_gatekeeper_rejection_claims_workflow_control(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_gatekeeper_control(sample_workdir), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Run a GateKeeper rejection control in the host Agent plane.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    step = result["next_step"]
    gatekeeper_output = _agent_native_rejected_gatekeeper_output(step)
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=gatekeeper_output,
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    control_step = result["next_step"]
    assert result["complete"] is False
    assert control_step["step_id"] == "control__gatekeeper_repair"
    assert control_step["role"]["archetype"] == "guide"
    assert control_step["role_dispatch"]["target_agent"] == "loopora-guide"

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(control_step["run_id"]),
            step_id=str(control_step["step_id"]),
            output=_agent_native_step_output(control_step),
            host_dispatch=_agent_native_host_dispatch("codex", control_step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    run_id = str(result["run"]["id"])
    run_dir = Path(result["run"]["runs_dir"])
    events = service.stream_events(run_id, limit=300)
    evidence_ledger = read_jsonl(run_dir / "evidence" / "ledger.jsonl")

    assert not any(event["event_type"] == "agent_native_controls_deferred" for event in events)
    assert any(
        event["event_type"] == "control_triggered"
        and event["payload"]["signal"] == "gatekeeper_rejected"
        and event["payload"]["control_id"] == "gatekeeper_repair"
        for event in events
    )
    assert any(
        event["event_type"] == "control_completed"
        and event["payload"]["signal"] == "gatekeeper_rejected"
        and event["payload"]["evidence_refs"]
        for event in events
    )
    assert any(entry["evidence_kind"] == "control" and "control:gatekeeper_rejected" in entry["verifies"] for entry in evidence_ledger)
