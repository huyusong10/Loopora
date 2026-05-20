from __future__ import annotations

from agent_adapter_helpers import *

def test_cli_agent_loop_terminal_unproven_reports_lifecycle_without_complete(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal_loop")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep terminal replay honest about evidence.",
                "loop_fit_reasons": ["A later Agent pass can add missing proof."],
                "judgment_tradeoffs": ["Never equate run lifecycle with task proof."],
                "execution_strategy": ["Continue from the missing audit evidence."],
                "local_governance": ["Record the task verdict before another pass."],
                "role_postures": [
                    {
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Report unproven evidence as unproven.",
                    }
                ],
                "success_surface": ["Audit evidence proves the user-visible flow."],
                "fake_done_states": ["A succeeded run with missing evidence is not done."],
                "evidence_preferences": ["Use project-owned checks and artifact paths."],
                "residual_risk": "No residual risk may hide missing audit proof.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakeService:
        def start_agent_loop(self, _adapter: str, *, workdir: Path, context_id: str = "", entry_source: str = "", execute_async: bool = True):
            _ = (workdir, context_id, entry_source, execute_async)
            return {
                "execution_plane": "agent_native",
                "run": {
                    "id": "run_terminal_loop",
                    "status": "succeeded",
                    "run_status": "succeeded",
                    "runs_dir": str(layout.run_dir),
                    "task_verdict": {
                        "status": "insufficient_evidence",
                        "source": "gatekeeper",
                        "summary": "Audit proof is still missing.",
                    },
                },
                "run_path": "/runs/run_terminal_loop",
                "started_new_run": False,
                "complete": True,
                "task_next_action": {
                    "kind": "continue_evidence",
                    "next_loop_command": "/loopora-run",
                    "guidance": "Run lifecycle is complete, but the task is not proven.",
                    "task_verdict_summary": "Audit proof is still missing.",
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(workdir), "--context-id", "thread-1", "--no-web"],
    )

    assert result.exit_code == 0, result.stdout
    assert "run_status: succeeded" in result.stdout
    assert "run_start: replayed_existing_terminal_run" in result.stdout
    assert f"run_contract_path: {layout.run_contract_path}" in result.stdout
    assert "task_verdict: insufficient_evidence" in result.stdout
    assert "task_next_action: Run lifecycle is complete, but the task is not proven." in result.stdout
    assert "next_loop_command: /loopora-run" in result.stdout
    assert "next_evidence_focus: Audit proof is still missing." in result.stdout
    assert "agent_native: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_native_task_verdict: insufficient_evidence" in result.stdout
    assert "agent_native: complete" not in result.stdout

def test_cli_agent_next_prints_run_contract_for_intermediate_capsule(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_next")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep intermediate capsules tied to frozen judgment.",
                "loop_fit_reasons": ["The next role needs the same proof bar as the first role."],
                "judgment_tradeoffs": ["Do not trade evidence coverage for fast handoff."],
                "execution_strategy": ["Claim the next proof gap before expanding scope."],
                "local_governance": ["Next role checks design and tests before submitting."],
                "role_postures": [
                    {
                        "role_name": "Inspector",
                        "archetype": "inspector",
                        "posture_notes": "Reject handoffs without evidence refs.",
                    }
                ],
                "completion_mode": "gatekeeper",
                "workflow": {
                    "preset": "quality_gate",
                    "collaboration_intent": "Inspector proof gaps must shape the release gate.",
                },
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}],
                    "coverage_targets": [
                        {"id": "done_when.check_001", "required": True},
                        {"id": "gatekeeper.finish", "required": True},
                    ],
                },
                "success_surface": ["Support can trace the refund authorization path."],
                "fake_done_states": ["A handoff without evidence refs is fake done."],
                "evidence_preferences": ["Use command output and audit artifacts."],
                "residual_risk": "Only documented support handoff risk may remain.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    class FakeService:
        def claim_agent_native_step(self, request: AgentNativeStepClaimRequest):
            assert request.adapter == "codex"
            assert request.workdir == workdir
            assert request.run_id == "run_next"
            return {
                "run": {
                    "id": "run_next",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "runs_dir": str(layout.run_dir),
                    "task_verdict": {
                        "status": "failed",
                        "summary": "Previous GateKeeper rejected the pass because evidence was non-supporting.",
                    },
                },
                "run_path": "/runs/run_next",
                "next_step": {
                    "step_id": "inspector_step",
                    "iter": 1,
                    "step_order": 0,
                    "role": {"name": "Inspector"},
                    "role_dispatch": {
                        "target_agent": "loopora-inspector",
                        "target_agent_config_path": ".codex/agents/loopora-inspector.toml",
                    },
                    "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
                    "inputs": {"evidence_query": {"archetypes": ["builder"], "limit": 12}},
                    "required_coverage": {
                        "status": "weak",
                        "covered_check_count": 1,
                        "missing_check_count": 1,
                        "top_gaps": [
                            {"target_id": "done_when.check_001", "status": "weak", "text": "Authorization proof is still weak."},
                        ],
                    },
                    "known_evidence_count": 4,
                    "known_evidence_ids": ["ev_builder", "ev_contract"],
                    "known_evidence_refs": [
                        {
                            "id": "ev_builder",
                            "step_id": "builder_step",
                            "role_name": "Builder",
                            "result": "completed",
                            "claim": "Builder supplied output but no proof artifact.",
                            "gatekeeper_support": "non_supporting",
                            "gatekeeper_support_reason": "no proof artifact",
                            "coverage_target_ids": [],
                            "artifact_refs": [
                                {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
                            ],
                        },
                        {
                            "id": "ev_contract",
                            "step_id": "contract_inspection_step",
                            "role_name": "Contract Inspector",
                            "result": "blocked",
                            "claim": "Inspector blocked the primary journey.",
                            "gatekeeper_support": "non_supporting",
                            "gatekeeper_support_reason": "result is blocked",
                            "coverage_target_ids": ["done_when.check_001"],
                        },
                    ],
                    "iteration_repair": {
                        "active": True,
                        "source_step_id": "gatekeeper_step",
                        "source_role": "GateKeeper",
                        "status": "blocked",
                        "summary": "GateKeeper rejected the prior pass.",
                        "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                        "recommended_next_action": "Produce direct project-owned proof before asking GateKeeper to pass again.",
                        "evidence_refs": ["ev_gatekeeper_block"],
                        "top_gaps": [
                            {
                                "target_id": "done_when.check_001",
                                "status": "blocked",
                                "source_section": "Done When",
                                "reason": "Evidence reported this target as blocked.",
                                "text": "The primary user flow works end to end.",
                                "evidence_refs": ["ev_gatekeeper_block"],
                            }
                        ],
                    },
                    "context_path": "iterations/iter_000/steps/01__inspector_step/input.context.json",
                    "capsule_path": "iterations/iter_000/steps/01__inspector_step/capsule.json",
                    "submit_hint": {
                        "command": "loopora agent codex submit --run-id run_next",
                        "result_file_contract": "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
                        "result_template_path": ".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json",
                        "result_outbox_dir": ".loopora/agent_outbox/codex",
                    },
                },
                "complete": False,
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_next",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "run_status: awaiting_agent" in result.stdout
    assert f"run_contract_path: {layout.run_contract_path}" in result.stdout
    assert "judgment_contract_summary: Keep intermediate capsules tied to frozen judgment." in result.stdout
    assert "check_mode: specified" in result.stdout
    assert "completion_mode: gatekeeper" in result.stdout
    assert "workflow_preset: quality_gate" in result.stdout
    assert "workflow_collaboration_intent: Inspector proof gaps must shape the release gate." in result.stdout
    assert "check_count: 1" in result.stdout
    _assert_cli_list(result.stdout, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    _assert_cli_list(result.stdout, "loop_fit_reasons", "The next role needs the same proof bar as the first role.")
    _assert_cli_list(result.stdout, "judgment_tradeoffs", "Do not trade evidence coverage for fast handoff.")
    _assert_cli_list(result.stdout, "execution_strategy", "Claim the next proof gap before expanding scope.")
    _assert_cli_list(result.stdout, "local_governance", "Next role checks design and tests before submitting.")
    _assert_cli_list(result.stdout, "role_postures", "Inspector: Reject handoffs without evidence refs.")
    _assert_cli_list(result.stdout, "success_surface", "Support can trace the refund authorization path.")
    _assert_cli_list(result.stdout, "fake_done_states", "A handoff without evidence refs is fake done.")
    _assert_cli_list(result.stdout, "evidence_preferences", "Use command output and audit artifacts.")
    assert "residual_risk: Only documented support handoff risk may remain." in result.stdout
    assert "next_step_id: inspector_step" in result.stdout
    assert "next_role: Inspector" in result.stdout
    assert "next_target_agent: loopora-inspector" in result.stdout
    assert "next_target_agent_config: .codex/agents/loopora-inspector.toml" in result.stdout
    assert "dispatch_next: invoke loopora-inspector with the next context/capsule paths below; do not perform this role inline" in result.stdout
    assert "next_action_policy: read_only, can_block" in result.stdout
    assert "required_coverage: weak; required checks 1 covered / 1 missing" in result.stdout
    assert "- done_when.check_001: [weak] Authorization proof is still weak." in result.stdout
    assert "next_context_path: iterations/iter_000/steps/01__inspector_step/input.context.json" in result.stdout
    assert "known_evidence_count: 4" in result.stdout
    assert "known_evidence_scope: filtered by evidence_query archetypes=builder limit=12" in result.stdout
    assert "iteration_repair_source: gatekeeper_step (GateKeeper)" in result.stdout
    assert "iteration_repair_next_action: Produce direct project-owned proof before asking GateKeeper to pass again." in result.stdout
    assert "known_evidence_refs:" in result.stdout
    assert "ev_contract result=blocked support=non_supporting reason=result is blocked" in result.stdout
    assert "result_template_contract: Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit." in result.stdout
    assert "result_template_fill: open the template, replace null placeholders in result, keep loopora_host_dispatch, then submit the filled copy" in result.stdout
    _assert_cli_handoff_contract_paths(
        result.stdout,
        capsule_fragment="iterations/iter_000/steps/01__inspector_step/capsule.json",
        template_fragment=".loopora/agent_outbox/codex/run_next__inspector_step.result.template.json",
        outbox_fragment=".loopora/agent_outbox/codex",
    )
    assert "submit_hint: loopora agent codex submit --run-id run_next" in result.stdout

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_next",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 0, json_result.stdout
    _assert_agent_next_json_summary(json_result.stdout)

def test_cli_agent_submit_prints_terminal_task_verdict(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_terminal")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep the evidence standard frozen through terminal submit.",
                "loop_fit_reasons": ["Later role outputs can drift without the frozen contract."],
                "judgment_tradeoffs": ["Direct proof beats narrative confidence."],
                "execution_strategy": ["Collect audit evidence before terminal closure."],
                "local_governance": ["Inspector verifies tests/ evidence before terminal closure."],
                "role_postures": [
                    {
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Separate run success from task proof.",
                    }
                ],
                "success_surface": ["Checkout instrumentation records the buyer action."],
                "fake_done_states": ["A story without audit evidence is fake done."],
                "evidence_preferences": ["Audit log command output is required."],
                "residual_risk": "Manual billing export remains a Support-owned follow-up.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_terminal",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"passed": True},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_terminal",
                    "status": "succeeded",
                    "run_status": "succeeded",
                    "runs_dir": str(layout.run_dir),
                    "task_verdict": {
                        "status": "insufficient_evidence",
                        "source": "gatekeeper",
                        "summary": "Required coverage still lacks direct evidence.",
                    },
                },
                "run_path": "/runs/run_terminal",
                "next_step": None,
                "complete": True,
                "submitted_step": {
                    "step_id": "gatekeeper_step",
                    "status": "blocked",
                    "summary": "GateKeeper submitted terminal evidence with an insufficient-evidence verdict.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                    "blocking_items": ["gatekeeper_pass_has_unmanaged_residual_risk"],
                    "recommended_next_action": "Move the residual risk to a blocking issue or name the owner and follow-up.",
                    "handoff_absolute_path": str(layout.run_dir / "iterations" / "iter_000" / "steps" / "03__gatekeeper_step" / "handoff.json"),
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_terminal",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "run_status: succeeded" in result.stdout
    assert "submitted_step_id: gatekeeper_step" in result.stdout
    assert "submitted_status: blocked" in result.stdout
    _assert_cli_list(result.stdout, "submitted_evidence_refs", "ev_000_03_gatekeeper_step")
    _assert_cli_list(result.stdout, "submitted_blocking_items", "gatekeeper_pass_has_unmanaged_residual_risk")
    assert "submitted_next_action: Move the residual risk to a blocking issue or name the owner and follow-up." in result.stdout
    assert "submitted_handoff_path:" in result.stdout
    assert "03__gatekeeper_step/handoff.json" in result.stdout
    assert "submitted_summary: GateKeeper submitted terminal evidence with an insufficient-evidence verdict." in result.stdout
    assert f"run_contract_path: {layout.run_contract_path}" in result.stdout
    assert "judgment_contract_summary: Keep the evidence standard frozen through terminal submit." in result.stdout
    _assert_cli_list(result.stdout, "loop_fit_reasons", "Later role outputs can drift without the frozen contract.")
    _assert_cli_list(result.stdout, "judgment_tradeoffs", "Direct proof beats narrative confidence.")
    _assert_cli_list(result.stdout, "execution_strategy", "Collect audit evidence before terminal closure.")
    _assert_cli_list(result.stdout, "local_governance", "Inspector verifies tests/ evidence before terminal closure.")
    _assert_cli_list(result.stdout, "role_postures", "GateKeeper: Separate run success from task proof.")
    _assert_cli_list(result.stdout, "success_surface", "Checkout instrumentation records the buyer action.")
    _assert_cli_list(result.stdout, "fake_done_states", "A story without audit evidence is fake done.")
    _assert_cli_list(result.stdout, "evidence_preferences", "Audit log command output is required.")
    assert "residual_risk: Manual billing export remains a Support-owned follow-up." in result.stdout
    assert "task_verdict: insufficient_evidence" in result.stdout
    assert "task_verdict_source: gatekeeper" in result.stdout
    assert "task_verdict_summary: Required coverage still lacks direct evidence." in result.stdout
    assert "task_next_action: run lifecycle is complete but the task is not proven" in result.stdout
    assert "run /loopora-run again in this Agent session to start the next evidence pass" in result.stdout
    assert "next_loop_command: /loopora-run" in result.stdout
    assert "next_plan_action: open run_url and use Improve plan with evidence if the Loop itself needs adjustment" in result.stdout
    assert "next_evidence_focus: Required coverage still lacks direct evidence." in result.stdout
    assert "agent_native: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_native_task_verdict: insufficient_evidence" in result.stdout
    assert "agent_native: complete" not in result.stdout

def test_cli_agent_submit_json_preserves_terminal_task_next_action(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_terminal",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"passed": True},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_terminal",
                    "status": "succeeded",
                    "run_status": "succeeded",
                    "task_verdict": {
                        "status": "insufficient_evidence",
                        "source": "gatekeeper",
                        "summary": "Required coverage still lacks direct evidence.",
                    },
                },
                "run_path": "/runs/run_terminal",
                "next_step": None,
                "complete": True,
                "submitted_step": {
                    "step_id": "gatekeeper_step",
                    "status": "passed",
                    "summary": "GateKeeper submitted a passing role decision while Core kept the task verdict insufficient.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                    "blocking_items": ["missing_direct_terminal_proof"],
                    "recommended_next_action": "Continue evidence in a new run before passing.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / "run_terminal" / "handoff.json"),
                },
                "task_next_action": {
                    "kind": "continue_evidence",
                    "reason": "run_lifecycle_complete_task_not_proven",
                    "task_verdict_status": "insufficient_evidence",
                    "next_loop_command": "/loopora-run",
                    "guidance": "Run lifecycle is complete, but the task is not proven.",
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_terminal",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    payload_keys = list(payload)
    assert payload_keys.index("agent_submit_summary") < payload_keys.index("run")
    summary = payload["agent_submit_summary"]
    assert summary["run_id"] == "run_terminal"
    assert summary["run_status"] == "succeeded"
    assert summary["complete"] is True
    assert summary["submitted_step"]["step_id"] == "gatekeeper_step"
    assert summary["submitted_step"]["status"] == "passed"
    assert summary["submitted_step"]["evidence_refs"] == ["ev_000_03_gatekeeper_step"]
    assert summary["submitted_step"]["blocking_items"] == ["missing_direct_terminal_proof"]
    assert "recommended_next_action" not in summary["submitted_step"]
    assert summary["submitted_step"]["handoff_path"].endswith("run_terminal/handoff.json")
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_complete_task_not_proven"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_plan_action"] == "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
    assert summary["next_evidence_focus"] == "Required coverage still lacks direct evidence."
    assert summary["task_next_action"]["kind"] == "continue_evidence"
    assert payload["complete"] is True
    assert payload["run"]["task_verdict"]["status"] == "insufficient_evidence"
    assert payload["task_next_action"]["kind"] == "continue_evidence"
    assert payload["task_next_action"]["next_loop_command"] == "/loopora-run"

def test_cli_agent_submit_json_separates_active_step_lifecycle_from_task_proof(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_active",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "Builder submitted a non-terminal handoff."},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_active",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "task_verdict": {
                        "status": "not_evaluated",
                        "summary": "Required coverage targets still lack direct evidence.",
                    },
                },
                "run_path": "/runs/run_active",
                "next_step": {
                    "step_id": "contract_inspection_step",
                    "role": {"name": "Contract Inspector"},
                    "role_dispatch": {"target_agent": "loopora-inspector"},
                    "action_policy": {"workspace": "read_only", "can_block": True},
                    "submit_hint": {"command": "loopora agent codex submit --run-id run_active"},
                },
                "complete": False,
                "submitted_step": {
                    "step_id": "builder_step",
                    "status": "completed",
                    "summary": "Builder produced a handoff, but the task is not proven.",
                    "evidence_refs": ["ev_000_00_builder_step"],
                    "coverage_results": [
                        {
                            "target_id": "done_when.check_001",
                            "status": "covered",
                            "evidence_refs": ["ev_000_00_builder_step"],
                            "note": "Builder evidence was classified against the first target.",
                        }
                    ],
                    "blocking_items": [],
                    "recommended_next_action": "Inspect the handoff before claiming task proof.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / "run_active" / "handoff.json"),
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_active",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = payload["agent_submit_summary"]
    assert summary["run_status"] == "awaiting_agent"
    assert summary["complete"] is False
    assert summary["submitted_step"]["step_id"] == "builder_step"
    assert summary["submitted_step"]["coverage_result_counts"] == {"covered": 1}
    assert summary["submitted_step"]["coverage_results"][0]["target_id"] == "done_when.check_001"
    assert summary["submitted_step"]["coverage_results"][0]["status"] == "covered"
    assert "recommended_next_action" not in summary["submitted_step"]
    assert summary["next_step"]["step_id"] == "contract_inspection_step"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_yet_evaluated"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"

def test_cli_agent_submit_json_marks_active_failed_verdict_as_continue_evidence(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_active_failed",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"passed": True},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_active_failed",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "task_verdict": {
                        "status": "failed",
                        "summary": "GateKeeper rejected the pass because cited evidence was non-supporting.",
                    },
                },
                "run_path": "/runs/run_active_failed",
                "next_step": {
                    "step_id": "builder_step",
                    "role": {"name": "Builder"},
                    "role_dispatch": {"target_agent": "loopora-builder"},
                    "action_policy": {"workspace": "workspace_write"},
                    "submit_hint": {"command": "loopora agent codex submit --run-id run_active_failed"},
                },
                "complete": False,
                "submitted_step": {
                    "step_id": "gatekeeper_step",
                    "status": "blocked",
                    "summary": "GateKeeper blocked the pass.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                    "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                    "recommended_next_action": "No action needed.",
                    "handoff_absolute_path": str(workdir / ".loopora" / "runs" / "run_active_failed" / "handoff.json"),
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_active_failed",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    summary = json.loads(result.stdout)["agent_submit_summary"]
    assert summary["complete"] is False
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["next_evidence_focus"] == "GateKeeper rejected the pass because cited evidence was non-supporting."
    assert summary["submitted_step"]["recommended_next_action"].startswith("Produce new project-owned proof")

def test_cli_agent_submit_schema_error_prints_result_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_schema")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "step_id": "gatekeeper_step",
                        "role": {"name": "GateKeeper", "id": "gatekeeper", "archetype": "gatekeeper"},
                        "role_dispatch": {"target_agent": "loopora-gatekeeper"},
                        "context_absolute_path": str(layout.step_context_path(0, 3, "gatekeeper_step")),
                        "known_evidence_ids": ["ev_000_00_builder_step", "ev_000_01_inspector_step"],
                        "output_schema": {
                            "type": "object",
                            "properties": {
                                "priority_failures": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["error_code", "summary"],
                                        "properties": {
                                            "error_code": {"type": "string"},
                                            "summary": {"type": "string"},
                                        },
                                    },
                                }
                            },
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file = tmp_path / "bad-result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_schema",
                    "step_id": "gatekeeper_step",
                    "target_agent": "loopora-gatekeeper",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"priority_failures": ["required evidence gap"]},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError("agent-native result does not match output_schema: $.priority_failures[0] expected object, got string")

        def get_run(self, run_id: str):
            assert run_id == "run_schema"
            return {"id": "run_schema", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_schema",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    error_text = _error_text(result)
    assert result.exit_code == 1
    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in error_text
    assert f"result_file_to_repair: {result_file}" in error_text
    assert "active_step_id: gatekeeper_step" in error_text
    assert "active_role: GateKeeper" in error_text
    assert "active_target_agent: loopora-gatekeeper" in error_text
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in error_text
    schema_lookup = _assert_labeled_loopora_agent_command(error_text, "schema_lookup", "next")
    assert f"--workdir {workdir.resolve()}" in schema_lookup
    assert "--run-id run_schema" in schema_lookup
    assert "Traceback" not in error_text

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_schema",
            "--step-id",
            "gatekeeper_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    assert payload["ready"] is False
    assert payload["submit_repair"] == "repair_result_json"
    assert payload["result_file_to_repair"] == str(result_file)
    assert payload["active_step_id"] == "gatekeeper_step"
    assert payload["active_role"] == "GateKeeper"
    assert payload["active_target_agent"] == "loopora-gatekeeper"
    assert "$.priority_failures[0] must be an object with required fields: error_code, summary" in payload["repair_focus"]
    assert payload["schema_lookup"].endswith("--run-id run_schema --json --entry-source codex_project_skill")

def test_cli_agent_submit_unfilled_template_reports_multiple_schema_repairs(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_unfilled")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    output_schema = {
        "type": "object",
        "properties": {
            "attempted": {"type": "string"},
            "abandoned": {"type": "string"},
            "assumption": {"type": "string"},
            "summary": {"type": "string"},
            "changed_files": {"type": "array", "items": {"type": "string"}},
            "proof_files": {"type": "array", "items": {"type": "string"}},
            "proof_artifacts": {"type": "array", "items": {"type": "object"}},
            "artifact_paths": {"type": "array", "items": {"type": "string"}},
        },
    }
    result_outbox_dir = workdir / ".loopora" / "agent_outbox" / "codex"
    result_file = result_outbox_dir / "run_unfilled__builder_step.result.template.json"
    filled_result_file = result_outbox_dir / "run_unfilled__builder_step.result.json"
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "iter": 1,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_context_path(0, 0, "builder_step")),
                        "output_schema": output_schema,
                        "submit_hint": {
                            "result_template_absolute_path": str(result_file),
                            "result_file_absolute_path": str(filled_result_file),
                            "result_outbox_absolute_dir": str(result_outbox_dir),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_unfilled",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {
                    "attempted": None,
                    "abandoned": None,
                    "assumption": None,
                    "summary": None,
                    "changed_files": [None],
                    "proof_files": [None],
                    "proof_artifacts": [None],
                    "artifact_paths": [None],
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError(
                "agent-native result does not match output_schema: "
                "$.attempted expected string, got null; "
                "$.abandoned expected string, got null; "
                "$.assumption expected string, got null; "
                "$.summary expected string, got null; "
                "$.changed_files[0] expected string, got null; "
                "$.proof_files[0] expected string, got null"
            )

        def get_run(self, run_id: str):
            assert run_id == "run_unfilled"
            return {"id": "run_unfilled", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    plain = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_unfilled",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    plain_error = _error_text(plain)
    assert plain.exit_code == 1
    assert f"active_result_template: {result_file}" in plain_error
    assert f"active_result_file_to_write: {filled_result_file}" in plain_error
    assert f"result_outbox_dir: {result_outbox_dir}" in plain_error
    assert "do not overwrite the .result.template.json audit template" in plain_error

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_unfilled",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    assert payload["submit_repair"] == "repair_result_json"
    assert payload["active_step_id"] == "builder_step"
    assert payload["submitted_template_file"] is True
    assert payload["result_outbox_dir"] == str(result_outbox_dir)
    assert payload["active_result_file_to_write"] == str(filled_result_file)
    assert payload["agent_submit_repair_summary"]["active_result_file_to_write"] == str(filled_result_file)
    assert "save a filled result copy" in payload["next_repair_step"]
    assert "do not overwrite the .result.template.json audit template" in payload["next_repair_step"]
    assert str(filled_result_file) in payload["next_repair_step"]
    repair_focus = payload["repair_focus"]
    assert repair_focus[0] == (
        "replace null placeholders before submit: "
        "$.attempted, $.abandoned, $.assumption, $.summary, $.changed_files[0], $.proof_files[0], "
        "$.proof_artifacts[0], $.artifact_paths[0]"
    )
    assert "$.attempted must be string" in repair_focus
    assert "$.summary must be string" in repair_focus
    assert "$.changed_files[0] must be string" in repair_focus

def test_cli_agent_submit_host_dispatch_errors_report_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_dispatch")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "iter": 1,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_context_path(0, 0, "builder_step")),
                        "output_schema": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string"},
                                "changed_files": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_payload = {"summary": "simulated filled copy", "changed_files": []}
    result_file = tmp_path / "wrong-dispatch.result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_dispatch",
                    "iter": 1,
                    "step_id": "builder_step",
                    "step_order": 0,
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-gatekeeper",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": result_payload,
            }
        ),
        encoding="utf-8",
    )
    missing_dispatch_file = tmp_path / "missing-dispatch.result.json"
    missing_dispatch_file.write_text(json.dumps({"result": result_payload}), encoding="utf-8")

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError("agent-native submit used loopora-gatekeeper but expected loopora-builder")

        def get_run(self, run_id: str):
            assert run_id == "run_dispatch"
            return {"id": "run_dispatch", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    mismatch = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_dispatch",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert mismatch.exit_code == 1
    assert _error_text(mismatch) == ""
    mismatch_payload = json.loads(mismatch.stdout)
    assert mismatch_payload["submit_repair"] == "repair_result_json"
    assert mismatch_payload["active_step_id"] == "builder_step"
    assert mismatch_payload["agent_submit_repair_summary"]["active_iter"] == 1
    assert mismatch_payload["agent_submit_repair_summary"]["active_step_order"] == 0
    assert mismatch_payload["agent_submit_repair_summary"]["submitted_dispatch"]["step_id"] == "builder_step"
    assert mismatch_payload["agent_submit_repair_summary"]["submitted_dispatch"]["iter"] == 1
    assert mismatch_payload["agent_submit_repair_summary"]["submitted_dispatch"]["step_order"] == 0
    assert mismatch_payload["agent_submit_repair_summary"]["submitted_dispatch"]["actual_agent"] == "loopora-gatekeeper"
    assert mismatch_payload["active_target_agent"] == "loopora-builder"
    assert (
        "set loopora_host_dispatch.target_agent and actual_agent to loopora-builder, inline to false, "
        "and keep adapter/run_id/iter/step_id/step_order exact"
    ) in mismatch_payload["repair_focus"]
    assert "fix loopora_host_dispatch to match the active role dispatch" in mismatch_payload["next_repair_step"]
    assert "loopora-builder" in mismatch_payload["next_repair_step"]

    missing = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_dispatch",
            "--step-id",
            "builder_step",
            "--result-file",
            str(missing_dispatch_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert missing.exit_code == 1
    assert _error_text(missing) == ""
    missing_payload = json.loads(missing.stdout)
    assert missing_payload["submit_repair"] == "repair_result_json"
    assert missing_payload["error"] == "result wrapper must contain loopora_host_dispatch object"
    assert "use one wrapper JSON object with loopora_host_dispatch and result" in missing_payload["repair_focus"]
    assert "restore loopora_host_dispatch by copying it from the active result template" in missing_payload["next_repair_step"]

def test_cli_agent_submit_repair_json_summarizes_stale_step_and_unknown_evidence(monkeypatch, tmp_path: Path) -> None:
    fixture = _write_agent_submit_repair_fixture(tmp_path)
    workdir = fixture["workdir"]
    layout = fixture["layout"]
    active_template = fixture["active_template"]
    stale_result_file = fixture["stale_result_file"]
    bad_ref_file = fixture["bad_ref_file"]

    class FakeService:
        def submit_agent_native_step(self, request: AgentNativeStepSubmitRequest):
            if request.step_id == "builder_step":
                raise LooporaConflictError("submitted step_id does not match the claimed agent-native step")
            raise LooporaError("agent-native evidence_refs_unknown: invented_ev")

        def get_run(self, run_id: str):
            assert run_id == "run_submit_repair"
            return {"id": "run_submit_repair", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    stale = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="builder_step",
        result_file=stale_result_file,
    )

    assert stale.exit_code == 1
    assert _error_text(stale) == ""
    _assert_stale_submit_repair_payload(json.loads(stale.stdout), active_template=active_template)

    bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
    )

    assert bad_ref.exit_code == 1
    assert _error_text(bad_ref) == ""
    _assert_bad_ref_submit_repair_payload(json.loads(bad_ref.stdout))

    plain_bad_ref = _invoke_codex_submit(
        runner,
        workdir,
        run_id="run_submit_repair",
        step_id="contract_inspection_step",
        result_file=bad_ref_file,
        json_output=False,
    )

    plain_error = _error_text(plain_bad_ref)
    assert plain_bad_ref.exit_code == 1
    _assert_plain_bad_ref_submit_repair(plain_error)

def test_cli_agent_submit_invalid_json_prints_result_file_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_bad_json")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "capsule": {
                        "step_id": "builder_step",
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_context_path(0, 0, "builder_step")),
                        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
                        "submit_hint": {
                            "result_template_absolute_path": str(tmp_path / "run_bad_json__builder_step.result.template.json"),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file = tmp_path / "bad-json.result.json"
    result_file.write_text('{"loopora_host_dispatch": ', encoding="utf-8")

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_bad_json"
            return {"id": "run_bad_json", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_bad_json",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    error_text = _error_text(result)
    assert result.exit_code == 1
    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in error_text
    assert f"result_file_to_repair: {result_file}" in error_text
    assert "active_step_id: builder_step" in error_text
    assert "active_role: Builder" in error_text
    assert "active_target_agent: loopora-builder" in error_text
    assert "fix JSON syntax" in error_text
    schema_lookup = _assert_labeled_loopora_agent_command(error_text, "schema_lookup", "next")
    assert f"--workdir {workdir.resolve()}" in schema_lookup
    assert "--run-id run_bad_json" in schema_lookup
    assert "Traceback" not in error_text

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_bad_json",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    assert payload["ready"] is False
    assert payload["submit_repair"] == "repair_result_json"
    assert payload["result_file_to_repair"] == str(result_file)
    assert payload["active_step_id"] == "builder_step"
    assert payload["active_role"] == "Builder"
    assert payload["active_target_agent"] == "loopora-builder"
    assert any("fix JSON syntax" in item for item in payload["repair_focus"])
    assert payload["schema_lookup"].endswith("--run-id run_bad_json --json --entry-source codex_project_skill")

    missing_file = tmp_path / "missing-filled.result.json"
    missing = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_bad_json",
            "--step-id",
            "builder_step",
            "--result-file",
            str(missing_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert missing.exit_code == 1
    assert _error_text(missing) == ""
    missing_payload = json.loads(missing.stdout)
    assert missing_payload["result_file_to_repair"] == str(missing_file)
    assert any("create the filled result JSON file at result_file_to_repair" in item for item in missing_payload["repair_focus"])
    assert "create the missing filled result file" in missing_payload["next_repair_step"]
    assert "run_bad_json__builder_step.result.template.json" in missing_payload["next_repair_step"]

def test_cli_agent_submit_reports_workflow_errors_without_traceback(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_test",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "unreachable"},
            }
        ),
        encoding="utf-8",
    )

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise WorkflowError("workflow control max_fires_per_run must be between 1 and 20")

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "submit",
            "--workdir",
            str(workdir),
            "--run-id",
            "run_corrupt",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    assert "max_fires_per_run" in _error_text(result)
    assert "Traceback" not in _error_text(result)
