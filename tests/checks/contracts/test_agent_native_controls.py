from __future__ import annotations

from loopora.agent_native_step_view_context import agent_native_step_view_iteration_repair_context
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    Path,
    TestClient,
    _assert_agent_run_summary_continuation,
    _assert_codex_native_surface_summary,
    _assert_terminal_recovery_choice,
    _drive_agent_native_run_to_success,
    alignment_bundle_yaml,
    build_app,
    json,
)

def test_agent_native_gatekeeper_pass_with_missing_required_coverage_keeps_task_verdict_insufficient(
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
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)

    run = final["run"]
    task_verdict = run["task_verdict"]
    assert run["status"] == "succeeded"
    assert run["last_verdict_json"]["passed"] is True
    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["source"] == "gatekeeper"
    assert "Required coverage" in task_verdict["summary"]
    assert final["task_next_action"]["kind"] == "continue_evidence"
    assert final["task_next_action"]["task_verdict_status"] == "insufficient_evidence"
    assert final["task_next_action"]["next_loop_command"] == "/loopora-run"
    assert "Run lifecycle is complete, but the task is not proven" in final["task_next_action"]["guidance"]
    agent_entry_start = service.agent_entry_loop_start_projection(run["loop_id"])
    assert agent_entry_start["next_loop_action"] == "start_next_run_for_unproven_verdict"
    assert agent_entry_start["continuation_summary"]["previous_run_id"] == run["id"]
    assert agent_entry_start["continuation_summary"]["previous_task_verdict"]["status"] == "insufficient_evidence"
    assert agent_entry_start["continuation_summary"]["coverage"]["missing_check_count"] > 0
    assert agent_entry_start["continuation_summary"]["next_focus"]
    assert json.loads((Path(run["runs_dir"]) / "evidence" / "task_verdict.json").read_text(encoding="utf-8")) == task_verdict

def test_agent_loop_restarts_after_terminal_insufficient_evidence(
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
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)
    previous_run = final["run"]

    recovery = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    choice = recovery["choices"][0]
    assert recovery["action"] == "choose_recoverable_context"
    _assert_terminal_recovery_choice(
        choice,
        expected={
            "previous_run_id": previous_run["id"],
            "action": "continue_terminal_evidence",
            "status": "terminal_unproven",
            "verdict": "insufficient_evidence",
            "hint_text": "next evidence pass",
            "label_prefix": "Continue evidence from terminal run:",
            "summary_text": "Required coverage",
        },
    )

    continued = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert previous_run["status"] == "succeeded"
    assert previous_run["task_verdict"]["status"] == "insufficient_evidence"
    assert continued["started_new_run"] is True
    assert continued["complete"] is False
    assert continued["run"]["id"] != previous_run["id"]
    assert continued["run"]["status"] == "awaiting_agent"
    assert continued["run"]["loop_id"] == previous_run["loop_id"]
    continuation_summary = _assert_agent_run_summary_continuation(
        continued["agent_run_summary"],
        previous_run_id=previous_run["id"],
        previous_task_verdict_status="insufficient_evidence",
    )
    _assert_codex_native_surface_summary(continued["agent_run_summary"])
    assert continuation_summary["next_focus"]
    assert continued["next_step"]["execution_plane"] == "agent_native"
    step_instruction_context = json.loads(Path(continued["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))
    agent_step_view = json.loads(Path(continued["next_step"]["agent_step_view_absolute_path"]).read_text(encoding="utf-8"))
    continuation = step_instruction_context["continuation"]
    assert continuation["previous_run_id"] == previous_run["id"]
    assert continuation["previous_task_verdict"]["status"] == "insufficient_evidence"
    assert continuation["previous_task_verdict_path"].endswith("evidence/task_verdict.json")
    assert continuation["coverage"]["missing_check_count"] > 0
    assert continuation["coverage"]["target_count"] > 0
    assert continuation["coverage"]["missing_target_count"] > 0
    assert any(gap["target_id"] == "done_when.check_001" for gap in continuation["coverage"]["top_gaps"])
    assert agent_step_view["continuation"]["previous_run_id"] == previous_run["id"]
    assert previous_run["id"] in continued["next_step"]["prompt"]
    assert "insufficient_evidence" in continued["next_step"]["prompt"]
    client = TestClient(build_app(service=service))
    snapshot_response = client.get(f"/api/runs/{continued['run']['id']}/observation-snapshot")
    assert snapshot_response.status_code == 200
    current_step = snapshot_response.json()["current_agent_step"]
    assert current_step["continuation"]["previous_run_id"] == previous_run["id"]
    assert current_step["continuation"]["previous_task_verdict"]["status"] == "insufficient_evidence"
    assert current_step["continuation"]["coverage"]["missing_check_count"] > 0
    assert current_step["continuation"]["coverage"]["target_count"] > 0
    assert current_step["continuation"]["next_focus"]
    session = service.get_alignment_session(started["session"]["id"])
    assert session["linked_run_id"] == continued["run"]["id"]
    assert continued["binding"]["linked_run_id"] == continued["run"]["id"]
    assert service.get_run(previous_run["id"])["task_verdict"]["status"] == "insufficient_evidence"

def test_agent_continuation_focus_reads_bucket_labels_and_reasons(service_factory) -> None:
    service = service_factory(scenario="success")

    focus = service._agent_native_continuation_focus(
        {
            "buckets": {
                "blocking": [{"label": "Permission audit is missing."}],
                "weak": [{"reason": "Residual risk lacks an owner."}],
            }
        },
        {"top_gaps": [{"target_id": "done_when.audit", "text": "Audit command has no output."}]},
    )

    assert "Permission audit is missing." in focus
    assert "Residual risk lacks an owner." in focus
    assert "done_when.audit: Audit command has no output." in focus

def test_agent_native_iteration_repair_context_projects_blocked_previous_iteration() -> None:
    repair = agent_native_step_view_iteration_repair_context(
        {
            "iteration": {
                "iter_index": 1,
                "coverage_top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper may finish only after supporting evidence.",
                    }
                ],
            },
            "upstream": {
                "previous_iteration_summary": {
                    "iter": 0,
                    "step_handoffs": [
                        {
                            "source": {"step_id": "gatekeeper_step", "role_name": "GateKeeper"},
                            "status": "blocked",
                            "summary": "GateKeeper blocked the previous iteration.",
                            "blocking_items": ["gatekeeper_pass_has_unmanaged_residual_risk"],
                            "recommended_next_action": "Continue only after the blocking issues are resolved.",
                            "evidence_refs": ["ev_000_03_gatekeeper_step"],
                        }
                    ],
                }
            },
        }
    )

    assert repair["active"] is True
    assert repair["previous_iteration"] == 0
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["source_role"] == "GateKeeper"
    assert repair["blocking_items"][0].startswith("gatekeeper_pass_has_unmanaged_residual_risk:")
    assert "owner, follow-up, or acceptance path" in repair["blocking_items"][0]
    assert repair["recommended_next_action"] == (
        "Resolve the residual risk or make it managed with an owner, follow-up, or acceptance path before asking GateKeeper to pass again."
    )
    assert repair["evidence_refs"] == ["ev_000_03_gatekeeper_step"]
    assert repair["top_gaps"][0]["target_id"] == "gatekeeper.finish"

def test_agent_native_iteration_repair_explains_non_supporting_gatekeeper_refs() -> None:
    repair = agent_native_step_view_iteration_repair_context(
        {
            "iteration": {
                "iter_index": 1,
                "coverage_top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper may finish only after supporting evidence.",
                    }
                ],
            },
            "upstream": {
                "previous_iteration_summary": {
                    "iter": 0,
                    "step_handoffs": [
                        {
                            "source": {"step_id": "gatekeeper_step", "role_name": "GateKeeper"},
                            "status": "blocked",
                            "summary": "GateKeeper rejected the pass attempt.",
                            "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                            "recommended_next_action": "No action needed.",
                            "evidence_refs": ["ev_000_03_gatekeeper_step"],
                        }
                    ],
                }
            },
        }
    )

    assert repair["blocking_items"][0].startswith("gatekeeper_pass_refs_not_supporting_evidence:")
    assert "not blocked, failed, rejected, or errored" in repair["blocking_items"][0]
    assert repair["recommended_next_action"].startswith("Produce new project-owned proof")

def test_agent_native_iteration_repair_does_not_repeat_resolved_target_specific_blocker() -> None:
    repair = agent_native_step_view_iteration_repair_context(
        {
            "iteration": {
                "iter_index": 2,
                "coverage_top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper needs a fresh verdict.",
                    },
                    {
                        "target_id": "fake_done.risk_004",
                        "status": "missing",
                        "text": "Handoff evidence still needs review.",
                    },
                ],
            },
            "upstream": {
                "previous_iteration_summary": {
                    "iter": 1,
                    "step_handoffs": [
                        {
                            "source": {"step_id": "gatekeeper_step", "role_name": "GateKeeper"},
                            "status": "blocked",
                            "summary": "GateKeeper blocked the previous iteration.",
                            "blocking_items": [
                                "browser_journey_capture_missing",
                                "check_004",
                                "Capture a browser/UI run for create, update, filter, and audit replay before passing.",
                            ],
                            "recommended_next_action": "Capture a browser/UI run for create, update, filter, and audit replay before passing.",
                            "evidence_refs": ["ev_001_03_gatekeeper_step"],
                        }
                    ],
                }
            },
        }
    )

    assert repair["active"] is True
    assert repair["blocking_items"] == []
    assert "browser/UI" not in repair["recommended_next_action"]
    assert repair["recommended_next_action"].startswith("Continue from the current coverage gaps")
    assert repair["top_gaps"][0]["target_id"] == "gatekeeper.finish"

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
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
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

    continued = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

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
