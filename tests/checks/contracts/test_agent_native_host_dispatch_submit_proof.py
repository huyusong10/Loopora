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
    pytest,
)


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
