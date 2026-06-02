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
    read_jsonl,
)


EXPECTED_CONTROL_MISSING_CHECK_COUNT = 2


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
    assert control_context["iteration"]["missing_check_count"] == EXPECTED_CONTROL_MISSING_CHECK_COUNT
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
