from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    json,
)


def test_agent_native_submit_uses_active_step_order_zero_before_state_cursor(
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
            message="Keep first-step submit artifacts anchored to the claimed active step.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["active_step"]["step_order"] == 0
    state["step_index"] = 7
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    result = service.submit_agent_native_step(
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

    expected_output = layout.step_output_raw_path(0, 0, str(step["step_id"]))
    wrong_cursor_output = layout.step_output_raw_path(0, 7, str(step["step_id"]))
    assert result["submitted_step"]["iter"] == 0
    assert result["submitted_step"]["step_order"] == 0
    assert expected_output.exists()
    assert not wrong_cursor_output.exists()
