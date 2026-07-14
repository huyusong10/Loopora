from __future__ import annotations

import json

from agent_adapter_test_support import _assert_cli_list, cli_agent_adapter_commands


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
    assert "submitted_next_action: Produce new project-owned proof" in evidence_gate_output
    assert "cite a non-blocked supporting evidence ref" in evidence_gate_output

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
    assert "submitted_next_action: Produce new project-owned proof" in none_action_output
    assert "cite a non-blocked supporting evidence ref" in none_action_output

    custom_blocked_step = {
        "step_id": "custom_check_step",
        "status": "blocked",
        "evidence_refs": ["ev_custom"],
        "blocking_items": ["custom_role_blocker: produce direct audit evidence before continuing"],
        "recommended_next_action": "No action needed.",
    }
    cli_agent_adapter_commands._print_agent_submitted_step(custom_blocked_step)

    custom_blocked_output = capsys.readouterr().out
    custom_blocked_summary = cli_agent_adapter_commands._agent_submitted_step_summary(custom_blocked_step)
    assert "submitted_next_action: No action needed." not in custom_blocked_output
    assert "submitted_next_action: Resolve the listed blocking items before continuing evidence." in custom_blocked_output
    assert custom_blocked_summary["recommended_next_action"] == "Resolve the listed blocking items before continuing evidence."


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

    assert "submitted_coverage_result_scope: submitted_role_raw_classifications_not_aggregated_coverage" in output
    assert "submitted_coverage_result_counts: covered=1 weak=1" in output
    assert "submitted_coverage_results:" in output
    assert "- done_when.check_001 covered refs=ev_builder:" in output
    assert "API authorization and idempotency are directly tested." in output
    assert "- done_when.check_002 weak refs=ev_builder:" in output
    assert "Provider retry is present but rollback proof is incomplete." in output
    assert summary["coverage_result_scope"] == "submitted_role_raw_classifications_not_aggregated_coverage"
    assert summary["coverage_result_counts"] == {"covered": 1, "weak": 1}
    assert summary["coverage_results_preview"][0] == {
        "target_id": "done_when.check_001",
        "status": "covered",
        "evidence_refs": ["ev_builder"],
    }
    assert "coverage_results" not in summary


def test_agent_cli_submitted_step_json_summary_bounds_long_coverage_notes() -> None:
    long_note = "Inspector observation. " * 400
    submitted_step = {
        "step_id": "contract_inspection_step",
        "status": "completed",
        "coverage_results": [
            {
                "target_id": f"done_when.check_{index:03d}",
                "status": "covered",
                "evidence_refs": [f"ev_{index:03d}"],
                "note": long_note,
            }
            for index in range(12)
        ],
    }

    summary = cli_agent_adapter_commands._agent_submitted_step_summary(submitted_step)
    encoded = json.dumps(summary)

    assert summary["coverage_result_counts"] == {"covered": 12}
    assert summary["coverage_results_omitted"] == 9
    assert len(summary["coverage_results_preview"]) == 3
    assert all("note" not in item for item in summary["coverage_results_preview"])
    assert long_note not in encoded
    assert len(encoded) < 1200
