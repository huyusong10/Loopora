from __future__ import annotations

from agent_adapter_test_support import _assert_cli_list, cli_agent_adapter_commands


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
    assert "iteration_continuation: previous iteration completed without closing the run" in output
    assert "address current coverage gaps in this next pass" in output
    assert "iteration_repair_source: gatekeeper_step (GateKeeper)" in output
    assert "iteration_repair_blocking_items:" in output
    assert "gatekeeper_pass_has_unmanaged_residual_risk: Manual export risk remains." in output
    assert "iteration_repair_next_action: Move the risk to blocking_issues" in output
    assert "remove it, or name an owner before passing." in output
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
    assert "iteration_repair_next_action: Produce new project-owned proof" in output
    assert "cite a non-blocked supporting evidence ref" in output
