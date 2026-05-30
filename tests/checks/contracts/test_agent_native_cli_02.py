from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepClaimRequest,
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    RunArtifactLayout,
    _assert_agent_next_json_summary,
    _assert_agent_next_plain_work_panel,
    _assert_cli_handoff_contract_paths,
    _assert_cli_list,
    _assert_cli_native_dispatch_contract,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _mkdir,
    agent_work_panel,
    assert_agent_v3_envelope,
    cli,
    json,
)


def test_agent_work_panel_distinguishes_terminal_unproven_and_proven_next_actions() -> None:
    terminal_unproven = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "insufficient_evidence"}},
            "complete": True,
            "task_next_action": {
                "kind": "continue_evidence",
                "guidance": "Run lifecycle is complete, but the task is not proven.",
            },
        }
    )
    proven = agent_work_panel(
        {
            "run": {"id": "run_panel", "task_verdict": {"status": "passed"}},
            "complete": True,
        }
    )

    assert terminal_unproven["state"] == "needs_more_evidence"
    assert terminal_unproven["next_action"] == (
        "Task proof is still missing; run /loopora-run again in this Agent session to continue evidence."
    )
    assert "complete" not in terminal_unproven["next_action"].lower()
    assert proven["state"] == "task_proven"
    assert proven["next_action"] == "Task verdict passed; no new evidence pass starts unless the task scope changes."


def test_cli_agent_next_prints_run_contract_for_intermediate_capsule(monkeypatch, tmp_path: Path) -> None:
    workdir = _mkdir(tmp_path / "project")
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
                    "native_todo": {
                        "recommended": True,
                        "not_evidence": True,
                        "host_policy": (
                            "Create or update the host's official todo/progress list when available; "
                            "do not cite todo completion as Loopora evidence."
                        ),
                        "items": [
                            "Read agent_v3_envelope.summary and the step contract.",
                            "Invoke loopora-inspector through the host-native role agent mechanism.",
                            "Fill the result template with schema-shaped output and preserve loopora_host_dispatch.",
                            "Submit the filled result and read agent_v3_envelope.summary before continuing.",
                        ],
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
                    "agent_step_view_path": "iterations/iter_000/steps/01__inspector_step/agent_step_view.json",
                    "step_contract_path": "iterations/iter_000/steps/01__inspector_step/step_contract.json",
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
    _assert_agent_next_plain_work_panel(result.stdout)
    assert "run_status: awaiting_agent" in result.stdout
    _assert_agent_contract_strategy_output(result.stdout, layout)
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
    _assert_cli_native_dispatch_contract(result.stdout, "loopora-inspector")
    assert "next_action_policy: read_only, can_block" in result.stdout
    assert "required_coverage: weak; required checks 1 covered / 1 missing" in result.stdout
    assert "- done_when.check_001: [weak] Authorization proof is still weak." in result.stdout
    assert "next_context_path: iterations/iter_000/steps/01__inspector_step/input.context.json" in result.stdout
    assert "next_agent_step_view_path: iterations/iter_000/steps/01__inspector_step/agent_step_view.json" in result.stdout
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
        step_contract_fragment="iterations/iter_000/steps/01__inspector_step/step_contract.json",
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


def _assert_agent_contract_strategy_output(stdout: str, layout: RunArtifactLayout) -> None:
    assert f"run_contract_path: {layout.run_contract_path}" in stdout
    assert "judgment_contract_summary: Keep intermediate capsules tied to frozen judgment." in stdout
    assert "check_mode: specified" in stdout
    assert "completion_mode: gatekeeper" in stdout
    assert "strategy_preset: quality_gate" in stdout
    assert "strategy_collaboration_intent: Inspector proof gaps must shape the release gate." in stdout
    assert "workflow_preset:" not in stdout
    assert "workflow_collaboration_intent:" not in stdout


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
    _assert_codex_native_surface_plain(result.stdout)
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
    assert "agent_runner: lifecycle_closed_task_unproven" in result.stdout
    assert "agent_runner_task_verdict: insufficient_evidence" in result.stdout
    assert "task_proof_source: run.task_verdict" in result.stdout
    assert "run_lifecycle_source: result.complete" in result.stdout
    assert "agent_runner: complete" not in result.stdout


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
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit", summary_key="agent_submit_summary", status="complete"
    )
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
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_plan_action"] == "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
    assert summary["next_evidence_focus"] == "Required coverage still lacks direct evidence."
    assert summary["task_next_action"]["kind"] == "continue_evidence"
    _assert_codex_native_surface_summary(summary)
    assert summary["task_next_action"]["next_loop_command"] == "/loopora-run"
