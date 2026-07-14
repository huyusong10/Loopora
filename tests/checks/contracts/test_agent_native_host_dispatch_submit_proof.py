from __future__ import annotations

import json

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    LooporaConflictError,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _drive_agent_native_run_to_success,
    alignment_bundle_yaml,
    pytest,
)


def test_agent_native_submit_refreshes_latest_state_for_mid_run_monitoring(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    step = started["next_step"]
    host_dispatch = _agent_native_host_dispatch("codex", step)
    host_dispatch["attestation_source"] = "explicit_submit_flag"

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_step_output(step),
            host_dispatch=host_dispatch,
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    latest_state = json.loads(layout.latest_state_path.read_text(encoding="utf-8"))
    assert latest_state["latest_iteration"] == 0
    assert latest_state["latest_by_step"] == {
        "builder_step": "iterations/iter_000/steps/00__builder_step/handoff.json"
    }
    assert latest_state["latest_by_role"] == {"builder": "iterations/iter_000/steps/00__builder_step/handoff.json"}
    assert latest_state["latest_by_archetype"] == {"builder": "iterations/iter_000/steps/00__builder_step/handoff.json"}
    assert latest_state["latest_gatekeeper"] is None
    state = json.loads((layout.run_dir / "agent_native" / "state.json").read_text(encoding="utf-8"))
    assert state["host_dispatches"][0]["attestation_source"] == "explicit_submit_flag"
    submitted_event = next(
        event
        for event in service.stream_events(str(result["run"]["id"]), limit=100)
        if event["event_type"] == "agent_native_step_submitted"
    )
    assert submitted_event["payload"]["host_dispatch"]["attestation_source"] == "explicit_submit_flag"


def test_agent_native_submit_requires_matching_host_dispatch_proof(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Require native role dispatch proof.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    step = started["next_step"]
    raw_output_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).step_output_raw_path(
        int(step["iter"]),
        int(step["step_order"]),
        str(step["step_id"]),
    )

    with pytest.raises(LooporaConflictError, match="loopora_host_dispatch"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    for field in ("adapter", "run_id", "iter", "step_id", "step_order"):
        incomplete_dispatch = _agent_native_host_dispatch("codex", step)
        incomplete_dispatch.pop(field)
        with pytest.raises(LooporaConflictError, match=rf"{field} is required"):
            service.submit_agent_native_step(
                AgentNativeStepSubmitRequest(
                    adapter="codex",
                    workdir=sample_workdir,
                    run_id=str(step["run_id"]),
                    step_id=str(step["step_id"]),
                    output=_agent_native_step_output(step),
                    host_dispatch=incomplete_dispatch,
                    entry_source="codex_project_skill",
                )
            )
        assert not raw_output_path.exists()

    stale_dispatch = _agent_native_host_dispatch("codex", step)
    stale_dispatch["iter"] = int(step["iter"]) + 1
    with pytest.raises(LooporaConflictError, match="iter does not match the claimed agent-native step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=stale_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    stale_dispatch = _agent_native_host_dispatch("codex", step)
    stale_dispatch["step_order"] = int(step["step_order"]) + 1
    with pytest.raises(LooporaConflictError, match="step_order does not match the claimed agent-native step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=stale_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    bad_dispatch = _agent_native_host_dispatch("codex", step)
    bad_dispatch["actual_agent"] = "loopora-gatekeeper"
    with pytest.raises(LooporaConflictError, match="expected loopora-builder"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=bad_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    unavailable_output_dispatch = _agent_native_host_dispatch("codex", step)
    unavailable_output_dispatch["native_trace"] = {
        "available": True,
        "notes": "The subagent returned no output, so the main Orchestrator session constructed the wrapper from verified state.",
    }
    with pytest.raises(LooporaConflictError, match="role agent output is unavailable"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=unavailable_output_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()

    unsupported_source_dispatch = _agent_native_host_dispatch("codex", step)
    unsupported_source_dispatch["attestation_source"] = "caller_claimed_magic"
    with pytest.raises(LooporaConflictError, match="attestation_source must be one of"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=unsupported_source_dispatch,
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()


def test_agent_native_submit_audit_precedes_terminal_run_events(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)

    events = service.stream_events(str(final["run"]["id"]), limit=500)

    def event_index(event_type: str, step_id: str | None = None) -> int:
        for index, event in enumerate(events):
            payload = event.get("payload") or {}
            if event["event_type"] == event_type and (step_id is None or payload.get("step_id") == step_id):
                return index
        raise AssertionError(f"missing event {event_type} for step {step_id}")

    gatekeeper_submitted = event_index("agent_native_step_submitted", "gatekeeper_step")
    assert gatekeeper_submitted < event_index("step_handoff_written", "gatekeeper_step")
    assert gatekeeper_submitted < event_index("run_finished")
