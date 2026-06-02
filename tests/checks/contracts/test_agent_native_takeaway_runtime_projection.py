from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
)


EXPECTED_TAKEAWAY_MISSING_CHECK_COUNT = 2


def test_agent_native_takeaways_keep_active_iteration_open_after_role_handoff(
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
            message="Ship the focused starter experience with evidence gaps visible.",
            bundle_file=bundle_file,
            context_id="thread-active-takeaway",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-active-takeaway",
        execute_async=False,
    )
    builder_step = started["next_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            context_id="thread-active-takeaway",
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    snapshot = service.run_observation_snapshot(result["run"]["id"])
    iterations = snapshot["key_takeaways"]["iterations"]

    assert result["run"]["status"] == "awaiting_agent"
    assert result["submitted_step"]["step_id"] == "builder_step"
    assert result["submitted_step"]["evidence_refs"] == ["ev_000_00_builder_step"]
    assert result["submitted_step"]["summary"]
    assert Path(result["submitted_step"]["handoff_absolute_path"]).exists()
    assert result["next_step"]["step_id"] == "contract_inspection_step"
    assert len(iterations) == 1
    active_iteration = iterations[0]
    assert active_iteration["status"] == "running"
    assert active_iteration["summary"] == "Builder produced a structured handoff for downstream inspection."
    assert active_iteration["role_count"] == 1
    assert active_iteration["roles"][0]["status"] == "completed"
    assert active_iteration["coverage_status"] == "partial"
    assert active_iteration["missing_check_count"] == EXPECTED_TAKEAWAY_MISSING_CHECK_COUNT
    assert active_iteration["coverage_top_gaps"][0]["target_id"] == "done_when.check_001"
