from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    LooporaError,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _drive_agent_native_until_archetype,
    alignment_bundle_yaml,
    json,
    pytest,
    read_jsonl,
)


def test_agent_native_rejects_non_gatekeeper_unknown_coverage_result_refs(
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
            message="Reject invented evidence refs before non-GateKeeper output enters the ledger.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(
        service,
        result,
        adapter="codex",
        workdir=sample_workdir,
        archetype="inspector",
    )
    step = result["next_step"]

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["invented_ev"],
            "note": "The ref is not copied from known_evidence_ids.",
        }
    ]
    with pytest.raises(LooporaError, match="agent-native evidence_refs_unknown: invented_ev"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=inspector_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )

    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    assert not layout.step_output_raw_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).exists()
    ledger = read_jsonl(layout.evidence_ledger_path)
    assert not any(item.get("step_id") == step["step_id"] for item in ledger)


def test_agent_native_known_evidence_ids_empty_step_view_stays_closed(
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
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(
        service,
        result,
        adapter="codex",
        workdir=sample_workdir,
        archetype="inspector",
    )
    step = result["next_step"]
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "ev_000_00_builder_step" in state["active_step"]["step_instruction_context"]["evidence"]["known_ids"]
    state["active_step"]["agent_step_view"]["known_evidence_ids"] = []
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "The ref exists in context but not in the step view closed set.",
        }
    ]

    with pytest.raises(LooporaError, match="agent-native evidence_refs_unknown: ev_000_00_builder_step"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(step["run_id"]),
                step_id=str(step["step_id"]),
                output=inspector_output,
                host_dispatch=_agent_native_host_dispatch("codex", step),
                entry_source="codex_project_skill",
            )
        )

    assert not layout.step_output_raw_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).exists()
    ledger = read_jsonl(layout.evidence_ledger_path)
    assert not any(item.get("step_id") == step["step_id"] for item in ledger)
