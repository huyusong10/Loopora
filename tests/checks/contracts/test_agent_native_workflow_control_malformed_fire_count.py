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
    json,
)


def test_agent_native_malformed_control_fire_count_fails_closed(
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
            message="Treat malformed local control fire counts as already exhausted.",
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

    state_path = Path(result["run"]["runs_dir"]) / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["control_fire_counts"]["gatekeeper_repair"] = "1"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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

    events = service.stream_events(str(result["run"]["id"]), limit=500)

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    assert [event["event_type"] for event in events].count("control_triggered") == 1
    assert any(
        event["event_type"] == "control_skipped"
        and event["payload"]["control_id"] == "gatekeeper_repair"
        and event["payload"]["skip_reason"] == "max_fires_per_run"
        for event in events
    )
