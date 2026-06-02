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


def test_agent_native_workflow_control_respects_fire_limit_across_iterations(
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
            message="Enforce an agent-native workflow control fire limit across iterations.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    first_gatekeeper_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(first_gatekeeper_step["run_id"]),
            step_id=str(first_gatekeeper_step["step_id"]),
            output=_agent_native_rejected_gatekeeper_output(first_gatekeeper_step),
            host_dispatch=_agent_native_host_dispatch("codex", first_gatekeeper_step),
            entry_source="codex_project_skill",
        )
    )

    first_control_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(first_control_step["run_id"]),
            step_id=str(first_control_step["step_id"]),
            output=_agent_native_step_output(first_control_step),
            host_dispatch=_agent_native_host_dispatch("codex", first_control_step),
            entry_source="codex_project_skill",
        )
    )

    assert result["next_step"]["step_id"] == "builder_step"
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    second_gatekeeper_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(second_gatekeeper_step["run_id"]),
            step_id=str(second_gatekeeper_step["step_id"]),
            output=_agent_native_rejected_gatekeeper_output(second_gatekeeper_step),
            host_dispatch=_agent_native_host_dispatch("codex", second_gatekeeper_step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    run_id = str(result["run"]["id"])
    run_dir = Path(result["run"]["runs_dir"])
    events = service.stream_events(run_id, limit=500)
    evidence_ledger = read_jsonl(run_dir / "evidence" / "ledger.jsonl")

    assert [event["event_type"] for event in events].count("control_triggered") == 1
    assert [event["event_type"] for event in events].count("control_completed") == 1
    assert any(
        event["event_type"] == "control_skipped"
        and event["payload"]["signal"] == "gatekeeper_rejected"
        and event["payload"]["control_id"] == "gatekeeper_repair"
        and event["payload"]["skip_reason"] == "max_fires_per_run"
        for event in events
    )
    control_entries = [entry for entry in evidence_ledger if entry["evidence_kind"] == "control"]
    assert len(control_entries) == 1
    assert "control:gatekeeper_rejected" in control_entries[0]["verifies"]
