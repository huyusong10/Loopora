from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,
    WorkflowError,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _alignment_bundle_yaml_with_gatekeeper_control,
    alignment_bundle_yaml,
    json,
    pytest,
)


def test_agent_native_submit_revalidates_persisted_workflow_controls(
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
            message="Reject corrupted persisted workflow controls before accepting an Agent Runner step result.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    corrupted_workflow = json.loads(json.dumps(started["run"]["workflow_json"]))
    corrupted_workflow["controls"][0]["max_fires_per_run"] = 0
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_runs SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), started["run"]["id"]),
        )

    with pytest.raises(WorkflowError, match="max_fires_per_run"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )

    events = service.stream_events(str(started["run"]["id"]), limit=100)
    assert not any(event["event_type"] == "agent_native_step_submitted" for event in events)


def test_agent_native_submit_revalidates_persisted_workflow_inputs(
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
            message="Reject corrupted persisted workflow inputs before accepting an Agent Runner step result.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    raw_output_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).step_output_raw_path(
        int(step["iter"]),
        int(step["step_order"]),
        str(step["step_id"]),
    )
    corrupted_workflow = json.loads(json.dumps(started["run"]["workflow_json"]))
    corrupted_workflow["steps"][1]["inputs"]["evidence_query"]["archetypes"].append(False)
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_runs SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), started["run"]["id"]),
        )

    with pytest.raises(WorkflowError, match="must contain only strings"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=_agent_native_step_output(step),
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )
    assert not raw_output_path.exists()
