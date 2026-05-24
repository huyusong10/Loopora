from __future__ import annotations

from agent_adapter_helpers import *

def test_agent_run_recovery_context_title_truncates_with_ellipsis(service_factory) -> None:
    service = service_factory(scenario="success")

    title = service._alignment_context_title_from_session(
        {"transcript": [{"role": "user", "content": "Build a refund-admin safety audit flow that prevents unauthorized refunds, records provider failures, and preserves audit evidence."}]}
    )

    assert title.endswith("...")
    assert len(title) == 80

def test_cli_recoverable_context_omits_run_commands_for_not_ready_choice(capsys) -> None:
    cli_agent_adapter_commands._print_recoverable_context_choices(
        {
            "confidence": "ambiguous",
            "choices": [
                {
                    "action": "preview_not_ready",
                    "label_en": "Resume Agent run: not ready preview",
                    "option_id": "agent_run:align_pending",
                    "alignment_session_id": "align_pending",
                    "choice_status": "not_ready",
                    "choice_hint_en": "Not runnable yet; return to /loopora-plan or Web review before selecting it.",
                    "runnable": False,
                    "alignment_status": "idle",
                    "updated_at": "2026-05-19T20:28:10Z",
                    "preview_url": "http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending",
                    "preview_path": "/loops/new/bundle?alignment_session_id=align_pending",
                    "next_slash_command": "/loopora-run option:agent_run:align_pending",
                    "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_pending",
                    "next_plan_command": "/loopora-plan",
                }
            ],
        }
    )

    output = capsys.readouterr().out

    assert "choice_status: not_ready" in output
    assert "runnable: false" in output
    assert "alignment_status: idle" in output
    assert "updated_at: 2026-05-19T20:28:10Z" in output
    assert "preview_url: http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending" in output
    assert "preview_path: /loops/new/bundle?alignment_session_id=align_pending" in output
    assert "next_plan_command: /loopora-plan" in output
    assert "next_loop_command:" not in output
    assert "next_cli_command:" not in output
    assert "selection_hint: no runnable contexts are available" in output
    assert "next: no runnable choice is available; return to /loopora-plan or Web review" in output
    assert "next: for a runnable choice" not in output

def test_cli_recoverable_context_attaches_preview_urls_to_choices(monkeypatch) -> None:
    result = {
        "context_resolution": {
            "choices": [
                {
                    "action": "preview_not_ready",
                    "label_en": "Review unfinished preview",
                    "option_id": "agent_run:align_pending",
                    "runnable": False,
                    "preview_path": "/loops/new/bundle?alignment_session_id=align_pending",
                }
            ]
        }
    }

    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:8749"},
    )

    cli_agent_adapter_commands._attach_recoverable_context_preview_urls(result, no_web=False)

    choice = result["context_resolution"]["choices"][0]
    assert result["web"]["base_url"] == "http://127.0.0.1:8749"
    assert choice["preview_url"] == "http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending"
    assert cli_agent_adapter_commands._recoverable_context_choice_summary(choice)["preview_url"] == choice["preview_url"]

def test_cli_recoverable_context_prints_terminal_verdict_status(capsys) -> None:
    cli_agent_adapter_commands._print_recoverable_context_choices(
        {
            "confidence": "ambiguous",
            "choices": [
                {
                    "action": "replay_terminal_pass",
                    "label_en": "Replay terminal run: Ship the focused starter experience.",
                    "option_id": "agent_run:align_passed",
                    "alignment_session_id": "align_passed",
                    "linked_run_id": "run_passed",
                    "linked_run_status": "succeeded",
                    "choice_status": "terminal_passed",
                    "choice_hint_en": (
                        "Replay a terminal run whose task verdict already passed; "
                        "no new Agent work starts unless the task scope changes."
                    ),
                    "task_verdict_status": "passed",
                    "task_verdict_summary": "Required coverage has direct evidence.",
                    "runnable": True,
                    "alignment_status": "running_loop",
                    "updated_at": "2026-05-19T20:28:10Z",
                    "next_slash_command": "/loopora-run option:agent_run:align_passed",
                    "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_passed",
                },
                repair_choice := {
                    "action": "repair_failed_preview",
                    "label_en": "Repair Agent plan: older failed preview",
                    "option_id": "agent_run:align_failed",
                    "alignment_session_id": "align_failed",
                    "choice_status": "needs_repair",
                    "choice_hint_en": "Candidate plan failed validation; repair it with /loopora-plan before selecting it.",
                    "runnable": False,
                    "preview_path": "/loops/new/bundle?alignment_session_id=align_failed",
                    "validation_error": "bundle metadata.name is required",
                    "plan_file_to_repair": "/tmp/bad-bundle.yml",
                    "preview_plan_copy": "/tmp/preview-bundle.yml",
                    "next_repair_step": (
                        "repair the candidate plan file so it preserves repair_task_message and repair_focus in spec, roles, "
                        "workflow, and evidence rules; rerun repair_cli_command or repair_slash_command, then use /loopora-run "
                        "only after the preview is ready"
                    ),
                    "next_plan_command": "/loopora-plan",
                }
            ],
        }
    )

    output = capsys.readouterr().out

    assert "- replay_terminal_pass: Replay terminal run: Ship the focused starter experience." in output
    assert "choice_status: terminal_passed" in output
    assert "no new Agent work starts unless the task scope changes" in output
    assert "linked_run_status: succeeded" in output
    assert "task_verdict: passed" in output
    assert "task_verdict_summary: Required coverage has direct evidence." in output
    assert "preview_path: /loops/new/bundle?alignment_session_id=align_failed" in output
    assert "validation_error: bundle metadata.name is required" in output
    assert "repair_focus:" in output
    assert "add metadata.name so the plan has a stable reviewable identity" in output
    assert "plan_file_to_repair: /tmp/bad-bundle.yml" in output
    assert "preview_plan_copy: /tmp/preview-bundle.yml" in output
    assert "selection_hint: one runnable context is available" in output
    repair_summary = cli_agent_adapter_commands._recoverable_context_choice_summary(repair_choice)
    assert repair_summary["validation_error"] == "bundle metadata.name is required"
    assert repair_summary["repair_focus"] == ["add metadata.name so the plan has a stable reviewable identity"]

def test_cli_recoverable_context_list_keeps_runnable_choices_visible(capsys) -> None:
    non_runnable = [
        {
            "action": "preview_not_ready",
            "label_en": f"Unfinished preview {index}",
            "option_id": f"agent_run:align_unfinished_{index}",
            "alignment_session_id": f"align_unfinished_{index}",
            "choice_status": "not_ready",
            "choice_hint_en": "Not runnable yet; return to /loopora-plan or Web review before selecting it.",
            "runnable": False,
            "alignment_status": "idle",
            "updated_at": f"2026-05-19T20:2{index}:10Z",
            "next_plan_command": "/loopora-plan",
        }
        for index in range(5)
    ]
    runnable = [
        {
            "action": "start_ready_preview",
            "label_en": "Start READY preview: Ship the focused starter experience.",
            "option_id": "agent_run:align_ready",
            "alignment_session_id": "align_ready",
            "choice_status": "ready_preview",
            "choice_hint_en": "Start this READY preview as a run; choose this if it is the plan you just reviewed.",
            "runnable": True,
            "alignment_status": "ready",
            "updated_at": "2026-05-19T20:10:10Z",
            "next_slash_command": "/loopora-run option:agent_run:align_ready",
            "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_ready",
        },
        {
            "action": "replay_terminal_pass",
            "label_en": "Replay terminal run: Ship the focused starter experience.",
            "option_id": "agent_run:align_passed",
            "alignment_session_id": "align_passed",
            "linked_run_id": "run_passed",
            "linked_run_status": "succeeded",
            "choice_status": "terminal_passed",
            "choice_hint_en": "Replay a terminal run whose task verdict already passed; no new Agent work starts unless the task scope changes.",
            "task_verdict_status": "passed",
            "task_verdict_summary": "Required coverage has direct evidence.",
            "runnable": True,
            "alignment_status": "running_loop",
            "updated_at": "2026-05-19T20:09:10Z",
            "next_slash_command": "/loopora-run option:agent_run:align_passed",
            "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_passed",
        },
    ]

    cli_agent_adapter_commands._print_recoverable_context_choices(
        {
            "confidence": "ambiguous",
            "choices": [*non_runnable, *runnable],
            "selection_hint": (
                "2 runnable contexts are available; choose the exact option_id for the active, READY, "
                "or terminal context you mean; non-runnable contexts need plan repair or Web review."
            ),
        }
    )

    output = capsys.readouterr().out

    assert "context_choices: 7 total / 2 runnable / 5 non-runnable" in output
    assert "- start_ready_preview: Start READY preview: Ship the focused starter experience." in output
    assert "- replay_terminal_pass: Replay terminal run: Ship the focused starter experience." in output
    assert "next_loop_command: /loopora-run option:agent_run:align_ready" in output
    assert "next_loop_command: /loopora-run option:agent_run:align_passed" in output
    assert "recoverable_contexts_omitted: 2 (0 runnable / 2 non-runnable)" in output
    assert "selection_hint: 2 runnable contexts are available" in output
    assert "Unfinished preview 4" not in output

def test_cli_terminal_passed_task_next_action_explains_no_next_pass(capsys) -> None:
    cli_agent_adapter_commands._print_terminal_task_next_action(
        {"status": "passed", "summary": "Required coverage has direct evidence."}
    )

    output = capsys.readouterr().out

    assert "task_next_action: task verdict already passed; no new evidence pass will start unless the task scope changes" in output

def test_agent_run_recovery_failed_preview_choice_points_to_repair(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bad-bundle.yml"
    bundle_file.write_text("version: 1\nspec:\n  name: Refund admin\n", encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a refund admin workflow with audit and provider-failure evidence.",
            bundle_file=bundle_file,
            context_id="thread-failed",
        )
    )
    resolution = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    choice = resolution["choices"][0]

    assert generated["requires_candidate_repair"] is True
    assert resolution["action"] == "choose_recoverable_context"
    assert choice["alignment_session_id"] == generated["session"]["id"]
    assert choice["action"] == "repair_failed_preview"
    assert "repair" in choice["choice_hint_en"]
    assert choice["preview_path"] == f"/loops/new/bundle?alignment_session_id={generated['session']['id']}"
    assert choice["validation_error"]
    assert "metadata.name is required" in choice["validation_error"]
    assert choice["plan_file_to_repair"] == str(bundle_file)
    assert choice["preview_plan_copy"].endswith("/artifacts/bundle.yml")
    assert choice["next_repair_step"].startswith("repair the candidate plan file")
    _assert_non_runnable_recovery_choice_routes_to_plan(choice, expected_status="needs_repair")

def test_agent_cli_required_coverage_summary_labels_partial_as_evidence_status() -> None:
    summary = cli_agent_adapter_commands._required_coverage_summary(
        {
            "status": "partial",
            "covered_check_count": 0,
            "missing_check_count": 5,
        }
    )

    assert summary == "partial evidence; required checks 0 covered / 5 missing"

def test_agent_cli_required_coverage_summary_includes_target_counts() -> None:
    summary = cli_agent_adapter_commands._required_coverage_summary(
        {
            "status": "blocked",
            "covered_check_count": 5,
            "missing_check_count": 0,
            "target_count": 13,
            "covered_target_count": 5,
            "missing_target_count": 7,
            "blocked_target_count": 1,
        }
    )

    assert summary == "blocked; required checks 5 covered / 0 missing, 5/13 targets covered / 7 missing / 1 blocked"

def test_agent_cli_top_coverage_gaps_marks_blocking_status(capsys) -> None:
    cli_agent_adapter_commands._print_top_coverage_gaps(
        {
            "top_gaps": [
                {
                    "target_id": "done_when.check_001",
                    "status": "blocked",
                    "source_section": "Done When",
                    "text": "Admin permission still lacks proof.",
                }
            ]
        }
    )

    assert "- done_when.check_001: [blocked] [Done When] Admin permission still lacks proof." in capsys.readouterr().out

def test_agent_cli_current_step_marks_next_iteration_continuation(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 1,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {"target_agent": "loopora-builder"},
            "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            "required_coverage": {"status": "blocked", "covered_check_count": 0, "missing_check_count": 2, "top_gaps": []},
            "iteration_repair": {
                "active": True,
                "previous_iteration": 0,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "summary": "GateKeeper blocked the prior iteration because residual risk was unmanaged.",
                "blocking_items": [
                    "gatekeeper_pass_has_unmanaged_residual_risk: Manual export risk remains. Name an owner, follow-up, or acceptance path."
                ],
                "recommended_next_action": "Move the risk to blocking_issues, remove it, or name an owner before passing.",
                "evidence_refs": ["ev_000_03_gatekeeper_step"],
            },
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out
    assert "next_iteration: 1" in output
    assert "next_step_order: 0" in output
    assert "iteration_continuation: previous iteration completed without closing the run; address current coverage gaps in this next pass" in output
    assert "iteration_repair_source: gatekeeper_step (GateKeeper)" in output
    assert "iteration_repair_blocking_items:" in output
    assert "gatekeeper_pass_has_unmanaged_residual_risk: Manual export risk remains." in output
    assert "iteration_repair_next_action: Move the risk to blocking_issues, remove it, or name an owner before passing." in output
    _assert_cli_list(output, "iteration_repair_evidence_refs", "ev_000_03_gatekeeper_step")

def test_agent_cli_iteration_repair_suppresses_placeholder_next_action(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 1,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {"target_agent": "loopora-builder"},
            "iteration_repair": {
                "active": True,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
                "recommended_next_action": "No action needed.",
            },
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert "iteration_repair_next_action: No action needed." not in output
    assert "iteration_repair_next_action: Produce new project-owned proof or cite a non-blocked supporting evidence ref" in output

def test_agent_cli_current_step_prints_zero_known_evidence_count(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 0,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {"target_agent": "loopora-builder"},
            "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            "required_coverage": {"status": "pending", "covered_check_count": 0, "missing_check_count": 2, "top_gaps": []},
            "known_evidence_ids": [],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert "known_evidence_count: 0" in output
    assert "known_evidence_ids:" not in output

def test_agent_cli_current_step_explains_unclassified_known_evidence(capsys) -> None:
    next_step = {
        "step_id": "contract_inspection_step",
        "iter": 0,
        "step_order": 1,
        "role": {"name": "Contract Inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "required_coverage": {
            "status": "partial",
            "covered_check_count": 0,
            "missing_check_count": 4,
            "target_count": 14,
            "covered_target_count": 0,
            "weak_target_count": 0,
            "blocked_target_count": 0,
            "missing_target_count": 14,
            "top_gaps": [],
        },
        "known_evidence_count": 1,
        "known_evidence_ids": ["ev_000_00_builder_step"],
        "submit_hint": {},
    }

    cli_agent_adapter_commands._print_agent_current_step(next_step)
    summary = cli_agent_adapter_commands._agent_next_step_summary(next_step)

    output = capsys.readouterr().out

    expected_note = (
        "known evidence is citable, but coverage remains unverified until a review role returns "
        "coverage_results with exact target IDs"
    )
    assert f"coverage_classification_note: {expected_note}" in output
    assert summary["coverage_classification_note"] == expected_note

def test_agent_cli_current_step_explains_unclassified_new_evidence_after_blocked_coverage(capsys) -> None:
    next_step = {
        "step_id": "contract_inspection_step",
        "iter": 1,
        "step_order": 1,
        "role": {"name": "Contract Inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "required_coverage": {
            "status": "blocked",
            "covered_check_count": 1,
            "missing_check_count": 3,
            "target_count": 14,
            "covered_target_count": 3,
            "weak_target_count": 0,
            "blocked_target_count": 11,
            "missing_target_count": 0,
            "top_gaps": [
                {
                    "target_id": "done_when.check_002",
                    "status": "blocked",
                    "source_section": "Done When",
                    "text": "Rollback proof is still classified from the previous GateKeeper verdict.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                }
            ],
        },
        "known_evidence_count": 5,
        "known_evidence_ids": [
            "ev_000_00_builder_step",
            "ev_000_03_gatekeeper_step",
            "ev_001_00_builder_step",
        ],
        "known_evidence_refs": [
            {
                "id": "ev_000_03_gatekeeper_step",
                "archetype": "gatekeeper",
                "gatekeeper_support": "non_supporting",
                "coverage_target_ids": ["done_when.check_002"],
            },
            {
                "id": "ev_001_00_builder_step",
                "archetype": "builder",
                "gatekeeper_support": "supporting",
                "coverage_target_ids": [],
            },
        ],
        "submit_hint": {},
    }

    cli_agent_adapter_commands._print_agent_current_step(next_step)
    summary = cli_agent_adapter_commands._agent_next_step_summary(next_step)

    output = capsys.readouterr().out

    expected_note = (
        "ev_001_00_builder_step is citable, but coverage still reflects earlier classifications until "
        "a review role returns coverage_results for that evidence"
    )
    assert f"coverage_classification_note: {expected_note}" in output
    assert summary["coverage_classification_note"] == expected_note

def test_agent_cli_current_step_omits_unclassified_note_when_only_gatekeeper_finish_remains(capsys) -> None:
    next_step = {
        "step_id": "evidence_inspection_step",
        "iter": 1,
        "step_order": 2,
        "role": {"name": "Evidence Inspector"},
        "role_dispatch": {"target_agent": "loopora-inspector"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "required_coverage": {
            "status": "blocked",
            "covered_check_count": 4,
            "missing_check_count": 0,
            "target_count": 14,
            "covered_target_count": 13,
            "weak_target_count": 0,
            "blocked_target_count": 1,
            "missing_target_count": 0,
            "top_gaps": [
                {
                    "target_id": "gatekeeper.finish",
                    "status": "blocked",
                    "source_section": "Workflow",
                    "text": "GateKeeper must finish from the next verdict.",
                    "evidence_refs": ["ev_000_03_gatekeeper_step"],
                }
            ],
        },
        "known_evidence_count": 5,
        "known_evidence_ids": [
            "ev_000_00_builder_step",
            "ev_001_00_builder_step",
            "ev_001_01_contract_inspection_step",
        ],
        "known_evidence_refs": [
            {
                "id": "ev_001_00_builder_step",
                "archetype": "builder",
                "gatekeeper_support": "supporting",
                "coverage_target_ids": [],
            }
        ],
        "submit_hint": {},
    }

    cli_agent_adapter_commands._print_agent_current_step(next_step)
    summary = cli_agent_adapter_commands._agent_next_step_summary(next_step)

    output = capsys.readouterr().out

    assert "coverage_classification_note:" not in output
    assert "coverage_classification_note" not in summary

def test_agent_cli_current_step_prints_target_agent_config_availability(capsys, tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "agents" / "loopora-builder.toml"
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 0,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_absolute_path": str(config_path),
                "target_agent_config_exists": True,
            },
            "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            "required_coverage": {"status": "pending", "covered_check_count": 0, "missing_check_count": 2, "top_gaps": []},
            "known_evidence_ids": [],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert f"next_target_agent_config: {config_path}" in output
    assert "next_target_agent_config_exists: true" in output
    assert "dispatch_next: invoke loopora-builder" in output
    assert "dispatch_unavailable:" not in output

def test_agent_cli_current_step_prints_bounded_known_evidence_ids(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "inspector_step",
            "iter": 1,
            "step_order": 2,
            "parallel_group": "reviewers",
            "role": {"name": "Inspector"},
            "role_dispatch": {"target_agent": "loopora-inspector"},
            "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
            "required_coverage": {
                "status": "partial",
                "covered_check_count": 1,
                "missing_check_count": 1,
                "top_gaps": [{"target_id": "gatekeeper.finish", "evidence_refs": ["ev_gatekeeper_blocker"]}],
            },
            "inputs": {"evidence_query": {"archetypes": ["builder"], "limit": 12}},
            "known_evidence_ids": [f"ev_{idx:03d}" for idx in range(10)],
            "known_evidence_refs": [
                {
                    "id": "ev_006",
                    "step_id": "builder_step",
                    "role_name": "Builder",
                    "result": "completed",
                    "claim": "Builder produced a claim without direct proof.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "no proof artifact",
                    "coverage_target_ids": [],
                    "artifact_refs": [
                        {"label": "proof-file:tests/browser-journey.json", "path": "tests/browser-journey.json"}
                    ],
                },
                {
                    "id": "ev_009",
                    "step_id": "inspector_step",
                    "role_name": "Inspector",
                    "result": "blocked",
                    "claim": "Inspector blocked the primary journey.",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "result is blocked",
                    "coverage_target_ids": ["done_when.check_001"],
                },
            ],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert "known_evidence_count: 10" in output
    assert (
        "known_evidence_scope: filtered by evidence_query archetypes=builder limit=12 "
        "parallel_group=reviewers snapshot=group_start coverage_gap_refs=included"
    ) in output
    assert "known_evidence_ids_omitted: 2 older" in output
    _assert_cli_list(output, "known_evidence_ids", "ev_002", "ev_009")
    assert "known_evidence_refs:" in output
    assert "- ev_006 result=completed support=non_supporting reason=no proof artifact" in output
    assert "claim: Builder produced a claim without direct proof." in output
    assert "artifacts: proof-file:tests/browser-journey.json: tests/browser-journey.json" in output
    assert "- ev_009 result=blocked support=non_supporting reason=result is blocked" in output
    assert "coverage_targets: done_when.check_001" in output
    assert "- ev_000" not in output
    assert "- ev_001" not in output

def test_agent_next_json_summary_bounds_known_evidence_ids_to_latest_window() -> None:
    summary = cli_agent_adapter_commands._agent_next_step_summary(
        {
            "step_id": "gatekeeper_step",
            "known_evidence_count": 10,
            "known_evidence_ids": [f"ev_{idx:03d}" for idx in range(10)],
            "known_evidence_refs": [
                {
                    "id": "ev_009",
                    "step_id": "evidence_inspection_step",
                    "role_name": "Evidence Inspector",
                    "result": "completed",
                    "gatekeeper_support": "supporting",
                    "gatekeeper_support_reason": "review evidence verifies a passed check",
                }
            ],
        }
    )

    assert summary["known_evidence_count"] == 10
    assert summary["known_evidence_ids_omitted"] == 2
    assert summary["known_evidence_ids"] == [f"ev_{idx:03d}" for idx in range(2, 10)]
    assert summary["known_evidence_refs"][0]["id"] == "ev_009"

def test_agent_cli_submitted_step_prints_blocking_items_only_for_blocked_status(capsys) -> None:
    cli_agent_adapter_commands._print_agent_submitted_step(
        {
            "step_id": "builder_step",
            "status": "completed",
            "evidence_refs": ["ev_builder"],
            "blocking_items": ["No workspace changes were needed."],
            "recommended_next_action": "Continue to the inspector.",
            "handoff_absolute_path": "/tmp/run/handoff.json",
            "summary": "Builder completed.",
        }
    )

    completed_output = capsys.readouterr().out
    assert "submitted_status: completed" in completed_output
    _assert_cli_list(completed_output, "submitted_evidence_refs", "ev_builder")
    assert "submitted_blocking_items:" not in completed_output
    assert "submitted_next_action:" not in completed_output

    cli_agent_adapter_commands._print_agent_submitted_step(
        {
            "step_id": "gatekeeper_step",
            "status": "blocked",
            "evidence_refs": ["ev_gatekeeper"],
            "blocking_items": ["gatekeeper_pass_has_unmanaged_residual_risk"],
            "recommended_next_action": "Name an owner or move the risk to a blocker.",
        }
    )

    blocked_output = capsys.readouterr().out
    assert "submitted_status: blocked" in blocked_output
    _assert_cli_list(blocked_output, "submitted_blocking_items", "gatekeeper_pass_has_unmanaged_residual_risk")
    assert "owner, follow-up, or acceptance path" in blocked_output
    assert "submitted_next_action: Name an owner or move the risk to a blocker." in blocked_output

    cli_agent_adapter_commands._print_agent_submitted_step(
        {
            "step_id": "gatekeeper_step",
            "status": "blocked",
            "evidence_refs": ["ev_gatekeeper"],
            "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
            "recommended_next_action": "Continue only after the blocking issues are resolved.",
        }
    )

    evidence_gate_output = capsys.readouterr().out
    assert "gatekeeper_pass_refs_not_supporting_evidence" in evidence_gate_output
    assert "not blocked, failed, rejected, or errored" in evidence_gate_output
    assert "submitted_next_action: Produce new project-owned proof or cite a non-blocked supporting evidence ref" in evidence_gate_output

    cli_agent_adapter_commands._print_agent_submitted_step(
        {
            "step_id": "gatekeeper_step",
            "status": "blocked",
            "evidence_refs": ["ev_gatekeeper"],
            "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence"],
            "recommended_next_action": "No action needed.",
        }
    )

    none_action_output = capsys.readouterr().out
    assert "submitted_next_action: No action needed." not in none_action_output
    assert "submitted_next_action: Produce new project-owned proof or cite a non-blocked supporting evidence ref" in none_action_output

def test_agent_cli_submitted_step_summarizes_coverage_results(capsys) -> None:
    submitted_step = {
        "step_id": "contract_inspection_step",
        "status": "completed",
        "evidence_refs": ["ev_contract"],
        "coverage_results": [
            {
                "target_id": "done_when.check_001",
                "status": "covered",
                "evidence_refs": ["ev_builder"],
                "note": "API authorization and idempotency are directly tested.",
            },
            {
                "target_id": "done_when.check_002",
                "status": "weak",
                "evidence_refs": ["ev_builder"],
                "note": "Provider retry is present but rollback proof is incomplete.",
            },
        ],
        "handoff_absolute_path": "/tmp/run/handoff.json",
        "summary": "Inspector classified the Builder evidence.",
    }

    cli_agent_adapter_commands._print_agent_submitted_step(submitted_step)
    summary = cli_agent_adapter_commands._agent_submitted_step_summary(submitted_step)

    output = capsys.readouterr().out

    assert "submitted_coverage_result_counts: covered=1 weak=1" in output
    assert "submitted_coverage_results:" in output
    assert "- done_when.check_001 covered refs=ev_builder: API authorization and idempotency are directly tested." in output
    assert "- done_when.check_002 weak refs=ev_builder: Provider retry is present but rollback proof is incomplete." in output
    assert summary["coverage_result_counts"] == {"covered": 1, "weak": 1}
    assert summary["coverage_results"][0] == {
        "target_id": "done_when.check_001",
        "status": "covered",
        "evidence_refs": ["ev_builder"],
        "note": "API authorization and idempotency are directly tested.",
    }

def test_agent_native_blocking_summaries_explain_contract_target_tokens() -> None:
    expected = "check_001: required check id; see required_coverage.missing_check_ids and top_coverage_gaps for the contract text"

    assert cli_agent_adapter_commands._actionable_blocking_item("check_001") == expected
    assert service_agent_native._agent_native_actionable_blocking_item("check_001") == expected
    assert cli_agent_adapter_commands._actionable_blocking_item("done_when.check_001").startswith(
        "done_when.check_001: coverage target id"
    )
    assert service_agent_native._agent_native_actionable_blocking_item("gatekeeper.finish").startswith(
        "gatekeeper.finish: GateKeeper finish target"
    )

def test_agent_native_generated_cli_commands_preserve_loopora_home(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project with spaces"
    result_file = workdir / ".loopora" / "agent_outbox" / "codex" / "run_agent__iter000__step00__builder_step.result.json"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    expected_prefix = f"LOOPORA_HOME={shlex.quote(str(home))} LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill "

    run_command = agent_adapters.agent_loop_json_command("codex", workdir, entry_source="codex_project_skill")
    submit_command = service_agent_native._agent_native_submit_command(
        adapter="codex",
        run_id="run_agent",
        step_id="builder_step",
        entry_source="codex_project_skill",
        result_file=str(result_file),
    )
    next_command = cli_agent_adapter_commands._agent_next_command_hint(
        adapter="codex",
        workdir=workdir,
        context_id="",
        run_id="run_agent",
        entry_source="codex_project_skill",
    )
    repair_command = cli_agent_adapter_commands._agent_plan_cli_command(
        adapter="codex",
        workdir=str(workdir),
        message="Repair the focused deletion-flow Loop.",
        entry_source="codex_project_skill",
        bundle_file=str(workdir / "candidate.yml"),
    )
    next_commands = agent_adapters._adapter_install_next_commands("codex", workdir)
    check_recovery = agent_adapters._adapter_check_recovery(
        "codex",
        workdir,
        status={"status": "not_installed"},
        check_status="fail",
    )

    assert run_command.startswith(expected_prefix)
    assert submit_command.startswith(expected_prefix)
    assert next_command.startswith(expected_prefix)
    assert repair_command.startswith(expected_prefix)
    assert f"--workdir {shlex.quote(str(workdir))}" in run_command
    assert f"--result-file {shlex.quote(str(result_file))}" in submit_command
    assert f"--workdir {shlex.quote(str(workdir))}" in next_command
    assert f"--bundle-file {shlex.quote(str(workdir / 'candidate.yml'))}" in repair_command
    _assert_loopora_cli_command(
        next_commands["check"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        next_commands["agent_check"],
        f"loopora agent codex check --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["install_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["check_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )

def test_agent_next_summary_reports_dispatch_recovery_commands_when_target_config_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project"
    monkeypatch.setenv("LOOPORA_HOME", str(home))

    summary = cli_agent_adapter_commands._agent_next_summary(
        {
            "adapter": "codex",
            "workdir": str(workdir),
            "run": {"id": "run_next", "status": "awaiting_agent", "workdir": str(workdir)},
            "next_step": {
                "adapter": "codex",
                "step_id": "contract_inspection_step",
                "role": {"name": "Contract Inspector"},
                "role_dispatch": {
                    "target_agent": "loopora-inspector",
                    "target_agent_config_absolute_path": str(workdir / ".codex" / "agents" / "loopora-inspector.toml"),
                    "target_agent_config_exists": False,
                },
            },
        }
    )

    next_step = summary["next_step"]
    _assert_codex_native_surface_summary(summary)
    assert "dispatch_next" not in next_step
    assert next_step["target_agent_config_exists"] is False
    dispatch_unavailable = next_step["dispatch_unavailable"]
    assert dispatch_unavailable["reason"] == "target_agent_config_missing"
    assert dispatch_unavailable["target_agent"] == "loopora-inspector"
    _assert_loopora_cli_command(
        dispatch_unavailable["check_command"],
        f"loopora agent codex check --workdir {workdir}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        dispatch_unavailable["repair_command"],
        f"loopora init codex --workdir {workdir}",
        loopora_home=home,
    )
    assert "do not submit inline role work" in dispatch_unavailable["next"]
