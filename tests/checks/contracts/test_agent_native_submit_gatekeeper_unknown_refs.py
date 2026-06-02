from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    _drive_agent_native_until_archetype,
    alignment_bundle_yaml,
    json,
)


def test_agent_native_gatekeeper_blocks_unknown_coverage_result_refs(
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
            message="Require coverage target evidence refs to stay inside the known evidence set.",
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
        archetype="gatekeeper",
    )
    step = result["next_step"]

    gatekeeper_output = _agent_native_step_output(step)
    gatekeeper_output["coverage_results"] = [
        {
            "target_id": "fake_done.risk_001",
            "status": "covered",
            "evidence_refs": ["invented_ev"],
            "note": "This target-level evidence ref is not from known_evidence_ids.",
        }
    ]
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

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    normalized_gatekeeper_output = json.loads(
        layout.step_output_normalized_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).read_text(
            encoding="utf-8"
        )
    )
    assert normalized_gatekeeper_output["passed"] is False
    assert normalized_gatekeeper_output["blocking_issues"] == ["gatekeeper_coverage_evidence_refs_unknown: invented_ev"]


def test_agent_native_gatekeeper_blocks_unknown_top_level_evidence_refs(
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
            message="Require coverage target evidence refs to stay inside the known evidence set.",
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
        archetype="gatekeeper",
    )
    step = result["next_step"]

    gatekeeper_output = _agent_native_step_output(step)
    gatekeeper_output["evidence_refs"] = ["invented_ev"]
    gatekeeper_output["coverage_results"] = []
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

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    layout = RunArtifactLayout(Path(result["run"]["runs_dir"]))
    normalized_gatekeeper_output = json.loads(
        layout.step_output_normalized_path(int(step["iter"]), int(step["step_order"]), str(step["step_id"])).read_text(
            encoding="utf-8"
        )
    )
    assert normalized_gatekeeper_output["passed"] is False
    assert normalized_gatekeeper_output["blocking_issues"] == ["gatekeeper_evidence_refs_unknown: invented_ev"]
