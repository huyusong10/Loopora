from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    LooporaConflictError,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    append_jsonl,
    json,
    pytest,
    read_jsonl,
)


def test_agent_native_duplicate_submit_cannot_append_second_evidence_entry(
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
            message="Keep agent-native step submission single-accept.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    stale_claimed_state = json.loads(state_path.read_text(encoding="utf-8"))

    first_result = service.submit_agent_native_step(
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
    assert first_result["submitted_step"]["evidence_refs"] == ["ev_000_00_builder_step"]

    state_path.write_text(json.dumps(stale_claimed_state, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(LooporaConflictError, match="already submitted"):
        service.submit_agent_native_step(
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

    evidence_ids = [str(item.get("id") or "") for item in read_jsonl(layout.evidence_ledger_path)]
    assert evidence_ids.count("ev_000_00_builder_step") == 1


def test_agent_native_known_evidence_ids_dedupe_duplicate_ledger_entries(
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
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
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
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    builder_evidence = next(item for item in read_jsonl(layout.evidence_ledger_path) if item.get("id") == "ev_000_00_builder_step")
    append_jsonl(layout.evidence_ledger_path, builder_evidence)

    inspector_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(inspector_step["run_id"]),
            step_id=str(inspector_step["step_id"]),
            output=_agent_native_step_output(inspector_step),
            host_dispatch=_agent_native_host_dispatch("codex", inspector_step),
            entry_source="codex_project_skill",
        )
    )

    known_ids = result["next_step"]["known_evidence_ids"]
    assert known_ids == list(dict.fromkeys(known_ids))
    step_instruction_context = json.loads(Path(result["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))
    assert step_instruction_context["evidence"]["known_ids"] == list(dict.fromkeys(step_instruction_context["evidence"]["known_ids"]))
    template = json.loads(Path(result["next_step"]["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_known_ids = template["loopora_result_contract"]["known_evidence_ids"]
    assert template_known_ids == list(dict.fromkeys(template_known_ids))
