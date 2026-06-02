from __future__ import annotations

from loopora.context_flow import (
    render_handoff_list_section,
    render_previous_iteration_summary,
)


def test_previous_iteration_summary_keeps_blocking_items_as_next_round_inputs() -> None:
    handoff = {
        "source": {
            "step_order": 1,
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
        },
        "status": "blocked",
        "summary": "Evidence is still weak.",
        "blocking_items": ["permission proof missing", "audit trail unproven"],
        "evidence_refs": ["ev_000_01_gatekeeper"],
        "recommended_next_action": "Produce direct permission and audit evidence.",
    }
    summary = {
        "iter": 0,
        "workflow": [{"step_id": "builder_step"}, {"step_id": "gatekeeper_step"}],
        "step_handoffs": [handoff],
        "score": {"composite": 0.42, "delta": None, "passed": False},
        "stagnation": {
            "mode": "none",
            "evidence_progress_mode": "stalled",
            "covered_check_count": 0,
            "missing_check_count": 2,
            "consecutive_no_required_coverage_delta": 1,
        },
    }

    rendered = render_previous_iteration_summary(summary)

    assert 'blocking=["permission proof missing", "audit trail unproven"]' in rendered
    assert "evidence=[\"ev_000_01_gatekeeper\"]" in rendered
    assert "next=Produce direct permission and audit evidence." in rendered


def test_completed_handoff_list_keeps_blocking_items_for_downstream_roles() -> None:
    rendered = render_handoff_list_section(
        "Completed steps in this iteration",
        [
            {
                "source": {
                    "step_order": 0,
                    "role_name": "Contract Inspector",
                    "archetype": "inspector",
                },
                "status": "blocked",
                "summary": "Authorization check did not run.",
                "blocking_items": ["authorization coverage missing"],
                "evidence_refs": ["ev_000_00_inspector"],
                "recommended_next_action": "Run the authorization proof before GateKeeper.",
            }
        ],
        empty_text="No earlier steps have completed in this iteration yet.",
    )

    assert 'blocking=["authorization coverage missing"]' in rendered
    assert "evidence=[\"ev_000_00_inspector\"]" in rendered
    assert "next=Run the authorization proof before GateKeeper." in rendered
