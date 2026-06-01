from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,
    WorkflowError,
    _agent_native_host_dispatch,
    _agent_native_rejected_gatekeeper_output,
    _agent_native_step_output,
    _alignment_bundle_yaml_with_gatekeeper_control,
    _drive_agent_native_until_archetype,
    alignment_bundle_yaml,
    json,
    pytest,
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


def test_agent_native_workflow_control_skip_records_after_not_elapsed_event(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_gatekeeper_control(sample_workdir, after="1h"), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Skip an agent-native GateKeeper rejection control before its after window elapses.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    step = result["next_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_rejected_gatekeeper_output(step),
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    events = service.stream_events(str(result["run"]["id"]), limit=300)

    assert not any(event["event_type"] == "agent_native_controls_deferred" for event in events)
    assert not any(event["event_type"] == "control_triggered" for event in events)
    assert not any(event["event_type"] == "control_completed" for event in events)
    assert any(
        event["event_type"] == "control_skipped"
        and event["payload"]["signal"] == "gatekeeper_rejected"
        and event["payload"]["control_id"] == "gatekeeper_repair"
        and event["payload"]["skip_reason"] == "after_not_elapsed"
        for event in events
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


def test_agent_native_no_evidence_progress_control_claims_stalled_context(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(
        _alignment_bundle_yaml_with_gatekeeper_control(
            sample_workdir,
            signal="no_evidence_progress",
            control_id="coverage_stall_guidance",
            trigger_window=1,
        ),
        encoding="utf-8",
    )
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Surface stalled required evidence coverage in the host Agent plane.",
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

    control_step = result["next_step"]
    assert control_step["step_id"] == "control__coverage_stall_guidance"
    assert control_step["role"]["archetype"] == "guide"
    control_context = json.loads(Path(control_step["context_absolute_path"]).read_text(encoding="utf-8"))
    assert control_context["iteration"]["evidence_progress_mode"] == "stalled"
    assert control_context["iteration"]["coverage_status"] == "blocked"
    assert control_context["iteration"]["covered_check_count"] == 0
    assert control_context["iteration"]["missing_check_count"] == 2
    assert control_context["iteration"]["missing_check_ids"] == ["check_001", "check_002"]
    assert any(item["target_id"] == "done_when.check_001" for item in control_context["iteration"]["coverage_top_gaps"])
    assert control_context["iteration"]["consecutive_no_required_coverage_delta"] == 1
    assert control_context["current_step"]["control"]["signal"] == "no_evidence_progress"
    assert control_step["required_coverage"]["status"] == "blocked"
    assert control_step["required_coverage"]["evidence_progress_mode"] == "stalled"
    assert control_step["required_coverage"]["missing_check_ids"] == ["check_001", "check_002"]
    assert any(item["target_id"] == "done_when.check_001" for item in control_step["required_coverage"]["top_gaps"])
    assert 'Missing required check ids: ["check_001", "check_002"]' in control_step["prompt"]

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
    events = service.stream_events(run_id, limit=500)
    evidence_ledger = read_jsonl(run_dir / "evidence" / "ledger.jsonl")

    assert any(
        event["event_type"] == "control_triggered"
        and event["payload"]["signal"] == "no_evidence_progress"
        and "Required coverage did not improve" in event["payload"]["reason"]
        for event in events
    )
    assert any(entry["evidence_kind"] == "control" and "control:no_evidence_progress" in entry["verifies"] for entry in evidence_ledger)
