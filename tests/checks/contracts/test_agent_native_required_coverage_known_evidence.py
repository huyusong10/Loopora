from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    json,
)


def test_agent_native_required_coverage_refs_stay_known_when_evidence_query_filters_items(
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
            message="Keep blocked coverage evidence citable by the next Agent Native role.",
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
    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    blocking_output = {
        "execution_summary": {"total_checks": 1, "passed": 0, "failed": 1, "errored": 0, "total_duration_ms": 1},
        "check_results": [
            {
                "id": "check_001",
                "title": "Primary contract proof",
                "status": "failed",
                "notes": "The Builder evidence does not prove the first required target.",
            }
        ],
        "dynamic_checks": [],
        "tester_observations": "Contract Inspector blocks the first required target using the Builder evidence.",
        "coverage_results": [
            {
                "target_id": "done_when.check_001",
                "status": "blocked",
                "evidence_refs": [builder_evidence_id],
                "note": "Builder evidence is insufficient for the first required target.",
            }
        ],
    }

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(contract_step["run_id"]),
            step_id=str(contract_step["step_id"]),
            output=blocking_output,
            host_dispatch=_agent_native_host_dispatch("codex", contract_step),
            entry_source="codex_project_skill",
        )
    )

    evidence_step = result["next_step"]
    blocking_evidence_id = "ev_000_01_contract_inspection_step"
    assert evidence_step["step_id"] == "evidence_inspection_step"
    assert evidence_step["required_coverage"]["top_gaps"][0]["evidence_refs"] == [blocking_evidence_id]
    assert blocking_evidence_id in evidence_step["known_evidence_ids"]
    known_evidence_refs = {item["id"]: item for item in evidence_step["known_evidence_refs"]}
    assert known_evidence_refs[builder_evidence_id]["claim"]
    assert (
        known_evidence_refs[blocking_evidence_id]["claim"]
        == "Contract Inspector blocks the first required target using the Builder evidence."
    )
    assert known_evidence_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support_reason"] == "result is blocked"
    assert evidence_step["required_coverage"]["target_count"] >= evidence_step["required_coverage"]["covered_check_count"]
    assert "blocked_target_count" in evidence_step["required_coverage"]

    step_instruction_context = json.loads(Path(evidence_step["context_absolute_path"]).read_text(encoding="utf-8"))
    assert step_instruction_context["iteration"]["target_count"] == evidence_step["required_coverage"]["target_count"]
    assert blocking_evidence_id in step_instruction_context["evidence"]["known_ids"]
    assert any(item["id"] == blocking_evidence_id for item in step_instruction_context["evidence"]["items"])

    template = json.loads(Path(evidence_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    assert blocking_evidence_id in template["loopora_result_contract"]["known_evidence_ids"]
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[blocking_evidence_id]["role_name"] == "Contract Inspector"
    assert template_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert template_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"
