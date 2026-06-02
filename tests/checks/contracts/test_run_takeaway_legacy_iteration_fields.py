from __future__ import annotations

import pytest

from loopora.run_takeaways import build_legacy_iteration_takeaway, build_role_takeaway_from_handoff, display_iter


@pytest.mark.parametrize("iter_value", [True, "2", 1.5])
def test_takeaway_display_iter_requires_integer_sequence(iter_value) -> None:
    assert display_iter(iter_value) is None

    iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_run",
            "status": "succeeded",
            "current_iter": iter_value,
            "summary_md": "# Loopora Run Summary\n\nLegacy run completed.",
        }
    )

    assert iteration is not None
    assert iteration["iter"] == 0
    assert iteration["display_iter"] == 1


def test_takeaway_role_source_and_legacy_failure_fields_require_literal_values() -> None:
    role = build_role_takeaway_from_handoff(
        {
            "source": {
                "iter": "4",
                "step_order": "8",
                "step_id": "builder_step",
                "runtime_role": "generator",
            },
            "status": "passed",
            "summary": "done",
            "blocking_items": ["real blocker", True],
            "evidence_refs": ["ev_001", False],
        }
    )

    assert role["id"].startswith("iter-0-")
    assert role["step_order"] == 0
    assert role["blocking_item"] == "real blocker"
    assert role["evidence_refs"] == ["ev_001"]

    malformed_role = build_role_takeaway_from_handoff(
        {
            "source": {"iter": 0, "step_order": 1, "step_id": "bad_shape"},
            "status": "blocked",
            "summary": True,
            "recommended_next_action": 7,
            "blocking_items": "string blocker",
            "evidence_refs": "ev_bad",
        }
    )

    assert malformed_role["summary"] == ""
    assert malformed_role["next_action"] == ""
    assert malformed_role["blocking_item"] == ""
    assert malformed_role["evidence_refs"] == []

    malformed_identity_role = build_role_takeaway_from_handoff(
        {
            "source": {
                "iter": 0,
                "step_order": 0,
                "step_id": True,
                "role_name": True,
                "runtime_role": True,
                "archetype": True,
            },
            "status": "passed",
            "summary": "done",
        }
    )

    assert malformed_identity_role["role_name"] == "-"
    assert malformed_identity_role["step_id"] == ""
    assert malformed_identity_role["archetype"] == ""
    assert "True" not in malformed_identity_role["id"]

    legacy_gatekeeper_iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_blocker",
            "status": "failed",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {
                "passed": False,
                "blocking_issues": "full blocker",
                "hard_constraint_violations": [True, "hard blocker"],
            },
        }
    )

    assert legacy_gatekeeper_iteration is not None
    assert legacy_gatekeeper_iteration["roles"][0]["blocking_item"] == "full blocker"

    iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_run",
            "status": "failed",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {
                "passed": False,
                "priority_failures": [
                    {
                        "role": "generator",
                        "error_code": "provider_failed",
                        "attempts": "2",
                        "degraded": "false",
                    }
                ],
            },
        }
    )

    assert iteration is not None
    blocking_item = iteration["roles"][0]["blocking_item"]
    assert "provider_failed" in blocking_item
    assert "attempts=2" not in blocking_item
    assert "degraded" not in blocking_item
