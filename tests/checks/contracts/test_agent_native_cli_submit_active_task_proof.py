from __future__ import annotations

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    CliRunner,
    Path,
    _assert_codex_native_surface_summary,
    assert_agent_v3_compact_envelope,
    assert_agent_v3_envelope,
    cli,
    json,
)


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
                    "coverage_target_ids": ["done_when.check_001", "gatekeeper.finish"],
                    "coverage_targets": [
                        {
                            "id": "done_when.check_001",
                            "kind": "done_when",
                            "required": True,
                            "text": "Builder handoff has supporting evidence.",
                        },
                        {
                            "id": "gatekeeper.finish",
                            "kind": "gatekeeper",
                            "required": True,
                            "text": "GateKeeper closes from supporting evidence.",
                        },
                    ],
                    "submit_hint": {"command": "loopora agent codex submit --run-id run_active"},
                },
                "complete": False,
                "coverage_after_submit": {
                    "source": "evidence_coverage",
                    "status": "weak",
                    "required_coverage": "weak; required checks 1 covered / 0 missing, 1/2 targets covered / 1 missing",
                    "target_count": 2,
                    "covered_target_count": 1,
                    "weak_target_count": 0,
                    "missing_target_count": 1,
                    "blocked_target_count": 0,
                    "check_count": 1,
                    "covered_check_count": 1,
                    "missing_check_count": 0,
                    "top_gaps": [
                        {
                            "target_id": "evidence_preference.pref_006",
                            "status": "missing",
                            "reason": "No residual risk evidence has verified this advisory target.",
                            "text": "Residual risk:",
                        }
                    ],
                },
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
    summary, legacy = assert_agent_v3_envelope(
        payload, kind="agent_submit", summary_key="agent_submit_summary", status="active"
    )
    assert summary["run_status"] == "awaiting_agent"
    assert summary["complete"] is False
    assert summary["submitted_step"]["step_id"] == "builder_step"
    assert summary["submitted_step"]["coverage_result_scope"] == "submitted_role_raw_classifications_not_aggregated_coverage"
    assert summary["submitted_step"]["coverage_result_counts"] == {"covered": 1}
    assert summary["submitted_step"]["coverage_results_preview"][0]["target_id"] == "done_when.check_001"
    assert summary["submitted_step"]["coverage_results_preview"][0]["status"] == "covered"
    assert "coverage_results" not in summary["submitted_step"]
    _assert_coverage_after_submit_summary(summary)
    assert legacy["submitted_step"]["coverage_results"][0]["note"] == "Builder evidence was classified against the first target."
    assert "recommended_next_action" not in summary["submitted_step"]
    _assert_active_submit_next_step_summary(summary)
    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_yet_evaluated"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_active_task_not_proven"
    assert summary["task_proof_source"] == "run.task_verdict"
    assert summary["run_lifecycle_source"] == "result.complete"
    summary_keys = list(summary)
    assert summary_keys.index("agent_work_panel") < summary_keys.index("agent_surface")
    _assert_codex_native_surface_summary(summary)

    compact_result = runner.invoke(
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
            "--compact-json",
        ],
    )

    assert compact_result.exit_code == 0, compact_result.stdout
    compact_payload = json.loads(compact_result.stdout)
    compact_summary = assert_agent_v3_compact_envelope(
        compact_payload,
        kind="agent_submit",
        summary_key="agent_submit_summary",
        status="active",
    )
    assert compact_summary["submitted_step"]["step_id"] == "builder_step"
    assert compact_summary["submitted_step"]["coverage_result_scope"] == "submitted_role_raw_classifications_not_aggregated_coverage"
    assert compact_summary["submitted_step"]["coverage_result_counts"] == {"covered": 1}
    assert compact_summary["submitted_step"]["coverage_results_preview"][0]["target_id"] == "done_when.check_001"
    assert "coverage_results" not in compact_summary["submitted_step"]
    _assert_coverage_after_submit_summary(compact_summary)
    assert compact_summary["next_step"]["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    compact_summary_keys = list(compact_summary)
    assert compact_summary_keys.index("agent_work_panel") < compact_summary_keys.index("agent_surface")
    assert compact_payload["technical_handoff"]["next_submit_command"] == "loopora agent codex submit --run-id run_active"
    assert "next_role_dispatch_message" not in compact_payload["technical_handoff"]


def test_cli_agent_submit_compact_json_bounds_next_step_and_surface_handoff(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_bounded",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {"summary": "Builder submitted bounded-output proof."},
            }
        ),
        encoding="utf-8",
    )
    long_target_tail = "TARGET-LONG-DETAIL " * 200
    long_note_tail = "COVERAGE-NOTE-LONG-DETAIL " * 200
    coverage_target_ids = [f"done_when.check_{index:03d}" for index in range(24)]

    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            return {
                "run": {
                    "id": "run_bounded",
                    "status": "awaiting_agent",
                    "run_status": "awaiting_agent",
                    "task_verdict": {
                        "status": "not_evaluated",
                        "summary": "The next role still needs to inspect compact handoff paths.",
                    },
                },
                "run_path": "/runs/run_bounded",
                "workdir": str(workdir),
                "next_step": {
                    "step_id": "contract_inspection_step",
                    "role": {"name": "Contract Inspector"},
                    "role_dispatch": {
                        "target_agent": "loopora-inspector",
                        "target_agent_config_absolute_path": str(workdir / ".codex" / "agents" / "loopora-inspector.toml"),
                        "target_agent_config_exists": True,
                    },
                    "action_policy": {"workspace": "read_only", "can_block": True},
                    "required_coverage": {
                        "status": "partial",
                        "target_count": 24,
                        "covered_target_count": 1,
                        "missing_target_count": 23,
                        "top_gaps": [
                            {
                                "target_id": target_id,
                                "status": "missing",
                                "reason": f"Gap {index} still needs proof. {long_target_tail}",
                                "text": f"Long gap text {index}. {long_target_tail}",
                            }
                            for index, target_id in enumerate(coverage_target_ids[:8])
                        ],
                    },
                    "coverage_target_ids": coverage_target_ids,
                    "coverage_targets": [
                        {
                            "id": target_id,
                            "kind": "done_when",
                            "required": True,
                            "text": f"Long target text {index}. {long_target_tail}",
                        }
                        for index, target_id in enumerate(coverage_target_ids)
                    ],
                    "known_evidence_count": 12,
                    "known_evidence_ids": [f"ev_{index:03d}" for index in range(12)],
                    "known_evidence_refs": [
                        {
                            "id": f"ev_{index:03d}",
                            "step_id": "builder_step",
                            "role_name": "Task Builder",
                            "result": "completed",
                            "gatekeeper_support": "supporting",
                            "claim": f"Long citable claim {index}. {long_target_tail}",
                        }
                        for index in range(12)
                    ],
                    "context_absolute_path": str(workdir / ".loopora" / "runs" / "run_bounded" / "context.json"),
                    "step_contract_absolute_path": str(workdir / ".loopora" / "runs" / "run_bounded" / "step_contract.json"),
                    "submit_hint": {
                        "command": "loopora agent codex submit --run-id run_bounded --step-id contract_inspection_step",
                        "result_template_absolute_path": str(
                            workdir / ".loopora" / "agent_outbox" / "codex" / "run_bounded__contract_inspection_step.result.template.json"
                        ),
                        "result_file_absolute_path": str(
                            workdir / ".loopora" / "agent_outbox" / "codex" / "run_bounded__contract_inspection_step.result.json"
                        ),
                        "result_outbox_absolute_dir": str(workdir / ".loopora" / "agent_outbox" / "codex"),
                    },
                },
                "complete": False,
                "submitted_step": {
                    "step_id": "builder_step",
                    "status": "completed",
                    "summary": "Builder produced a long result; compact output should stay bounded.",
                    "evidence_refs": ["ev_000_00_builder_step"],
                    "coverage_results": [
                        {
                            "target_id": target_id,
                            "status": "covered",
                            "evidence_refs": ["ev_000_00_builder_step"],
                            "note": f"Long coverage result note {index}. {long_note_tail}",
                        }
                        for index, target_id in enumerate(coverage_target_ids)
                    ],
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
            "run_bounded",
            "--step-id",
            "builder_step",
            "--result-file",
            str(result_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
            "--compact-json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = assert_agent_v3_compact_envelope(
        payload,
        kind="agent_submit",
        summary_key="agent_submit_summary",
        status="active",
    )
    assert len(result.stdout.encode("utf-8")) < 18_000
    assert long_note_tail not in result.stdout
    assert long_target_tail not in result.stdout
    assert summary["submitted_step"]["coverage_result_counts"] == {"covered": 24}
    assert len(summary["submitted_step"]["coverage_results_preview"]) == 3
    assert summary["submitted_step"]["coverage_results_omitted"] == 21
    assert summary["next_step"]["coverage_target_ids"] == coverage_target_ids
    assert "coverage_targets" not in summary["next_step"]
    assert len(summary["next_step"]["coverage_targets_preview"]) == 3
    assert summary["next_step"]["coverage_targets_omitted"] == 21
    assert len(summary["next_step"]["top_coverage_gaps"]) == 3
    assert len(summary["next_step"]["known_evidence_refs"]) == 3
    assert "packaging" not in summary["agent_surface"]
    assert summary["agent_surface"]["entry_kind"] == "project_skill"
    assert summary["agent_surface"]["capability_contract"]["role_dispatch"] == "host_native"
    assert payload["technical_handoff"]["next_submit_command"] == (
        "loopora agent codex submit --run-id run_bounded --step-id contract_inspection_step"
    )
    assert "next_role_dispatch_message" not in payload["technical_handoff"]
    _assert_role_dispatch_message(
        summary["next_role_dispatch_message"],
        target_agent="loopora-inspector",
        expected_coverage_ids=None,
        require_paths=True,
    )
    assert "coverage_target_ids=" + ", ".join(coverage_target_ids[:8]) in summary["next_role_dispatch_message"]
    assert "known_evidence_ids=" + ", ".join(f"ev_{index:03d}" for index in range(4, 12)) in summary["next_role_dispatch_message"]
    assert long_note_tail not in summary["next_role_dispatch_message"]
    assert long_target_tail not in summary["next_role_dispatch_message"]


def _assert_coverage_after_submit_summary(summary: dict) -> None:
    coverage = summary["coverage_after_submit"]
    assert coverage["source"] == "evidence_coverage"
    assert coverage["status"] == "weak"
    assert coverage["target_count"] == 2
    assert coverage["missing_target_count"] == 1
    assert coverage["top_gaps"][0]["target_id"] == "evidence_preference.pref_006"


def _assert_active_submit_next_step_summary(summary: dict) -> None:
    assert summary["next_step_id"] == "contract_inspection_step"
    assert summary["next_target_agent"] == "loopora-inspector"
    assert summary["next_submit_command"] == "loopora agent codex submit --run-id run_active"
    assert summary["next_step"]["step_id"] == "contract_inspection_step"
    assert summary["next_step"]["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    assert summary["next_step"]["coverage_targets"][0] == {
        "id": "done_when.check_001",
        "kind": "done_when",
        "required": True,
        "text": "Builder handoff has supporting evidence.",
    }
    assert summary["next_role_dispatch_message"] == summary["next_step"]["role_dispatch_message"]
    _assert_role_dispatch_message(
        summary["next_role_dispatch_message"],
        target_agent="loopora-inspector",
        expected_coverage_ids="done_when.check_001, gatekeeper.finish",
        require_paths=False,
    )


def _assert_role_dispatch_message(
    message: str,
    *,
    target_agent: str,
    expected_coverage_ids: str | None,
    require_paths: bool,
) -> None:
    assert f"target_agent={target_agent}" in message
    assert "action_policy=read_only, can_block" in message
    if expected_coverage_ids is not None:
        assert f"coverage_target_ids={expected_coverage_ids}" in message
    assert "Use this exact string as the whole Agent/Task prompt" in message
    assert "prepend `You are running as`" in message
    assert "append `Do the following`" in message
    assert "return one raw wrapper JSON object only" in message
    assert "Main session writes/submits result" in message
    assert "Do not paste full CLI JSON" in message
    assert "full schemas" in message
    assert "large evidence ledgers" in message
    assert "wrapper examples" in message
    if require_paths:
        assert "context_path=" in message
        assert "step_contract_path=" in message
        assert "result_template=" in message
