from __future__ import annotations

from loopora.cli_agent_submit_repair_output import print_agent_submit_repair_plain


def test_submit_repair_plain_output_keeps_active_context_and_submitted_dispatch(capsys) -> None:
    print_agent_submit_repair_plain(
        {
            "result_file_to_repair": "/tmp/result.json",
            "active_step_id": "contract_inspection_step",
            "active_role": "Inspector",
            "active_target_agent": "loopora-inspector",
            "active_result_template": "/tmp/contract_inspection.result.template.json",
            "active_result_file_to_write": "/tmp/contract_inspection.result.json",
            "submitted_dispatch": {
                "run_id": "run_001",
                "step_id": "builder_step",
                "iter": 0,
                "step_order": 0,
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-gatekeeper",
                "dispatch_mode": "host_native_role_agent",
                "inline": False,
            },
            "active_known_evidence_ids": ["ev_000_00_builder_step"],
            "active_known_evidence_refs": [
                {
                    "id": "ev_000_00_builder_step",
                    "result": "completed",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "no proof artifact",
                    "claim": "Builder proof exists but remains weak.",
                    "coverage_target_ids": ["done_when.check_001", "done_when.check_002"],
                }
            ],
            "active_coverage_target_ids": ["done_when.check_001", "done_when.check_002"],
            "repair_focus": ["submit the active step_id exactly"],
            "next_repair_step": "discard the stale result file and fill the active result template",
            "schema_lookup": "loopora agent codex next --workdir /tmp --run-id run_001 --json",
        }
    )

    output = capsys.readouterr().err

    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in output
    assert "result_file_to_repair: /tmp/result.json" in output
    assert "active_step_id: contract_inspection_step" in output
    assert "active_result_file_to_write: /tmp/contract_inspection.result.json" in output
    assert "submitted_dispatch: run_id=run_001, step_id=builder_step, iter=0, step_order=0" in output
    assert "actual_agent=loopora-gatekeeper" in output
    assert "inline=False" in output
    assert "active_known_evidence_ids:" in output
    assert "- ev_000_00_builder_step result=completed support=non_supporting reason=no proof artifact" in output
    assert "claim: Builder proof exists but remains weak." in output
    assert "coverage_targets: done_when.check_001, done_when.check_002" in output
    assert "active_coverage_target_ids:" in output
    assert "- done_when.check_002" in output
    assert "repair_focus:" in output
    assert "- submit the active step_id exactly" in output
    assert "next_repair_step: discard the stale result file and fill the active result template" in output
    assert "schema_lookup: loopora agent codex next --workdir /tmp --run-id run_001 --json" in output
