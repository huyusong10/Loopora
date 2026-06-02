from __future__ import annotations

from loopora.agent_native_step_view_context import agent_native_step_view_iteration_repair_context


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
