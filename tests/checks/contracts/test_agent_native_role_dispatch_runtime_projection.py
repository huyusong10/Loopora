from __future__ import annotations

import shlex

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepClaimRequest,
    Path,
    alignment_bundle_yaml,
    json,
)


EXPECTED_MISSING_REQUIRED_CHECK_COUNT = 2


def test_agent_native_role_dispatch_projects_target_agent_config_availability(
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
            context_id="thread-dispatch-config",
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-dispatch-config",
        entry_source="codex_project_skill",
        execute_async=False,
    )

    dispatch = started["next_step"]["role_dispatch"]
    config_path = Path(dispatch["target_agent_config_absolute_path"])
    assert dispatch["target_agent_config_exists"] is False

    state_path = Path(started["run"]["runs_dir"]) / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["agent_step_view"]["submit_hint"]["command"] = (
        "loopora agent codex submit --run-id stale --step-id builder_step"
    )
    for key in ("result_file_absolute_path", "result_template_absolute_path", "result_outbox_absolute_dir"):
        state["active_step"]["agent_step_view"]["submit_hint"].pop(key, None)
    stale_coverage = {
        "status": "weak",
        "covered_check_count": 1,
        "missing_check_count": 1,
        "covered_check_ids": ["check_001"],
        "missing_check_ids": ["check_002"],
        "target_count": 9,
        "covered_target_count": 1,
        "weak_target_count": 0,
        "missing_target_count": 8,
        "blocked_target_count": 0,
        "top_gaps": [{"target_id": "done_when.check_002", "status": "missing"}],
    }
    state["active_step"]["agent_step_view"]["required_coverage"] = dict(stale_coverage)
    assert "context_packet" not in state["active_step"]
    state["active_step"]["step_instruction_context"]["iteration"].update(
        {
            "coverage_status": stale_coverage["status"],
            "covered_check_count": stale_coverage["covered_check_count"],
            "missing_check_count": stale_coverage["missing_check_count"],
            "covered_check_ids": stale_coverage["covered_check_ids"],
            "missing_check_ids": stale_coverage["missing_check_ids"],
            "target_count": stale_coverage["target_count"],
            "covered_target_count": stale_coverage["covered_target_count"],
            "weak_target_count": stale_coverage["weak_target_count"],
            "missing_target_count": stale_coverage["missing_target_count"],
            "blocked_target_count": stale_coverage["blocked_target_count"],
            "coverage_top_gaps": stale_coverage["top_gaps"],
        }
    )
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('name = "loopora-builder"\n', encoding="utf-8")
    refreshed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(
            adapter="codex",
            workdir=sample_workdir,
            context_id="thread-dispatch-config",
            run_id=started["run"]["id"],
            entry_source="codex_project_skill",
        )
    )
    snapshot = service.run_observation_snapshot(started["run"]["id"])

    assert refreshed["next_step"]["role_dispatch"]["target_agent_config_exists"] is True
    submit_hint = refreshed["next_step"]["submit_hint"]
    submit_command = submit_hint["command"]
    submit_tokens = shlex.split(submit_command)
    assert "--json" in submit_command
    assert '"$PWD"' not in submit_command
    assert submit_tokens[submit_tokens.index("--workdir") + 1] == str(sample_workdir.resolve())
    assert Path(submit_tokens[submit_tokens.index("--result-file") + 1]).is_absolute()
    assert Path(submit_tokens[submit_tokens.index("--result-file") + 1]).resolve() == Path(
        submit_hint["result_file_absolute_path"]
    ).resolve()
    assert refreshed["next_step"]["required_coverage"]["covered_check_count"] == 0
    assert refreshed["next_step"]["required_coverage"]["missing_check_count"] == EXPECTED_MISSING_REQUIRED_CHECK_COUNT
    assert refreshed["next_step"]["required_coverage"]["missing_check_ids"] == ["check_001", "check_002"]
    template_path = Path(refreshed["next_step"]["submit_hint"]["result_template_absolute_path"])
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert template["loopora_result_contract"]["required_coverage"]["covered_check_count"] == 0
    assert template["loopora_result_contract"]["required_coverage"]["missing_check_ids"] == ["check_001", "check_002"]
    assert snapshot["current_agent_step"]["target_agent_config_exists"] is True
    assert snapshot["current_agent_step"]["role_dispatch"]["target_agent_config_exists"] is True
