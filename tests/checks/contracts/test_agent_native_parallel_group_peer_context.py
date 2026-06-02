from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _alignment_bundle_yaml_with_peer_visible_parallel_review_inputs,
    json,
)


def test_agent_native_parallel_group_peer_context_uses_group_start_snapshot(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_peer_visible_parallel_review_inputs(sample_workdir), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Keep agent-native parallel reviewers isolated from peer outputs.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = result["next_step"]
    assert builder_step["action_policy"] == {
        "workspace": "workspace_write",
        "can_block": False,
        "can_finish_run": False,
    }
    assert builder_step["role"]["prompt_ref"].endswith("builder.md")
    assert "Keep implementation narrow" in builder_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    first_peer_step = result["next_step"]
    assert first_peer_step["step_id"] == "contract_inspection_step"
    assert first_peer_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": False,
    }
    assert first_peer_step["role"]["prompt_ref"].endswith("inspector.md")
    assert "contract-level proof" in first_peer_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(first_peer_step["run_id"]),
            step_id=str(first_peer_step["step_id"]),
            output=_agent_native_step_output(first_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", first_peer_step),
            entry_source="codex_project_skill",
        )
    )

    second_peer_step = result["next_step"]
    assert second_peer_step["step_id"] == "evidence_inspection_step"
    second_peer_context = json.loads(Path(second_peer_step["context_absolute_path"]).read_text(encoding="utf-8"))
    second_peer_handoff_steps = [item["source"]["step_id"] for item in second_peer_context["upstream"]["completed_steps_this_iteration"]]

    assert second_peer_handoff_steps == ["builder_step"]
    assert second_peer_context["evidence"]["known_ids"] == ["ev_000_00_builder_step"]
    assert second_peer_step["inputs"]["evidence_query"] == {"archetypes": ["builder", "inspector"], "limit": 12}
    assert second_peer_step["parallel_group"] == "inspection_pack"
    assert second_peer_step["known_evidence_ids"] == ["ev_000_00_builder_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(second_peer_step["run_id"]),
            step_id=str(second_peer_step["step_id"]),
            output=_agent_native_step_output(second_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", second_peer_step),
            entry_source="codex_project_skill",
        )
    )

    gatekeeper_step = result["next_step"]
    assert gatekeeper_step["step_id"] == "gatekeeper_step"
    assert gatekeeper_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": True,
    }
    assert gatekeeper_step["role"]["prompt_ref"].endswith("gatekeeper.md")
    assert "Close only when" in gatekeeper_step["role"]["posture_notes"]
    gatekeeper_context = json.loads(Path(gatekeeper_step["context_absolute_path"]).read_text(encoding="utf-8"))
    gatekeeper_handoff_steps = [item["source"]["step_id"] for item in gatekeeper_context["upstream"]["completed_steps_this_iteration"]]

    assert gatekeeper_handoff_steps == ["contract_inspection_step", "evidence_inspection_step"]
    assert {
        "ev_000_01_contract_inspection_step",
        "ev_000_02_evidence_inspection_step",
    }.issubset(set(gatekeeper_context["evidence"]["known_ids"]))
    events = service.stream_events(str(gatekeeper_step["run_id"]), limit=200)
    assert any(
        event["event_type"] == "parallel_group_started"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
    assert any(
        event["event_type"] == "parallel_group_finished"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
