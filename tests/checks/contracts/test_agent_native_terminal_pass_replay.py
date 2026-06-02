from __future__ import annotations

from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    Path,
    _assert_codex_native_surface_summary,
    _assert_terminal_recovery_choice,
    _drive_agent_native_run_to_success,
    alignment_bundle_yaml,
)


def test_agent_loop_replays_terminal_passed_task_verdict(
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
            message="Keep agent-native lifecycle success separate from evidence-backed task proof.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)
    previous_run = final["run"]
    service.repository.update_run(
        previous_run["id"],
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Required coverage has direct evidence.",
            "buckets": {"proven": [], "weak": [], "unproven": [], "blocking": [], "residual_risk": []},
        },
    )
    service.repository.update_alignment_session(
        started["session"]["id"],
        error_message=f"another active run is already using {sample_workdir.resolve()}",
    )

    recovery = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    choice = recovery["choices"][0]
    assert recovery["action"] == "choose_recoverable_context"
    _assert_terminal_recovery_choice(
        choice,
        expected={
            "previous_run_id": previous_run["id"],
            "action": "replay_terminal_pass",
            "status": "terminal_passed",
            "verdict": "passed",
            "hint_text": "no new Agent work starts unless the task scope changes",
            "label_prefix": "Replay terminal run:",
            "summary_text": "Required coverage has direct evidence.",
        },
    )

    continued = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )

    assert continued["started_new_run"] is False
    assert continued["complete"] is True
    result_keys = list(continued)
    assert result_keys.index("agent_run_summary") < result_keys.index("session")
    assert continued["agent_run_summary"]["run_id"] == previous_run["id"]
    assert continued["agent_run_summary"]["run_status"] == "succeeded"
    assert continued["agent_run_summary"]["complete"] is True
    assert continued["agent_run_summary"]["next_step_id"] == ""
    assert continued["agent_run_summary"]["task_verdict_status"] == "passed"
    assert continued["agent_run_summary"]["task_proven"] is True
    assert continued["agent_run_summary"]["task_outcome"] == "already_proven_no_new_evidence"
    assert continued["agent_run_summary"]["lifecycle_vs_task"] == "run_lifecycle_complete_task_proven"
    assert continued["agent_run_summary"]["task_proof_source"] == "run.task_verdict"
    assert continued["agent_run_summary"]["run_lifecycle_source"] == "result.complete"
    _assert_codex_native_surface_summary(continued["agent_run_summary"])
    assert continued["agent_run_summary"]["task_next_action"]["kind"] == "already_passed"
    assert continued["task_next_action"]["kind"] == "already_passed"
    assert continued["task_next_action"]["reason"] == "task_verdict_passed"
    assert continued["task_next_action"]["run_status"] == "succeeded"
    assert continued["task_next_action"]["task_verdict_status"] == "passed"
    assert continued["task_next_action"]["task_verdict_summary"] == "Required coverage has direct evidence."
    assert "no new evidence pass" in continued["task_next_action"]["guidance"]
    assert continued["session"]["error_message"] == ""
    assert continued["run"]["id"] == previous_run["id"]
    assert continued["next_step"] is None
    session = service.get_alignment_session(started["session"]["id"])
    assert session["linked_run_id"] == previous_run["id"]
    assert session["error_message"] == ""
    assert len(service.get_loop(previous_run["loop_id"])["runs"]) == 1
