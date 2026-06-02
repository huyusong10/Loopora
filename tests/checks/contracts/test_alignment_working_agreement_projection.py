from __future__ import annotations

from loopora.service_alignment_agreement_stage import (
    alignment_agreement_ready_stage_plan,
    alignment_agreement_readiness_checklist_issues,
    alignment_agreement_working_agreement,
)


def test_alignment_agreement_working_agreement_projects_stable_ready_payload() -> None:
    agreement = alignment_agreement_working_agreement(
        {
            "agreement_summary": "  Confirmed direction.  ",
            "readiness_checklist": {"loop_fit": True, "explicit_confirmation": True},
            "readiness_evidence": {"loop_fit": "Slow feedback needs governed evidence."},
        },
        captured_at="2026-05-29T00:00:00Z",
    )

    assert agreement == {
        "summary": "Confirmed direction.",
        "readiness_checklist": {"loop_fit": True, "explicit_confirmation": False},
        "readiness_evidence": {"loop_fit": "Slow feedback needs governed evidence."},
        "captured_at": "2026-05-29T00:00:00Z",
        "confirmed_at": "",
        "confirmation_message": "",
    }


def test_alignment_agreement_working_agreement_fails_closed_for_malformed_payload_parts() -> None:
    agreement = alignment_agreement_working_agreement(
        {
            "agreement_summary": None,
            "readiness_checklist": ["bad"],
            "readiness_evidence": ["bad"],
        },
        captured_at="now",
    )

    assert agreement["summary"] == ""
    assert agreement["readiness_checklist"] == {"explicit_confirmation": False}
    assert agreement["readiness_evidence"] == {}


def test_alignment_agreement_ready_stage_plan_projects_confirmation_boundary() -> None:
    working_agreement = {
        "summary": "Confirmed direction.",
        "readiness_checklist": {"loop_fit": True, "explicit_confirmation": False},
    }

    plan = alignment_agreement_ready_stage_plan(
        working_agreement,
        assistant_message="Please confirm this working agreement.",
        prefers_chinese=False,
    )

    assert plan.update_fields == {
        "alignment_stage": "agreement_ready",
        "working_agreement": working_agreement,
    }
    assert plan.output_updates["assistant_message"] == "Please confirm this working agreement."
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["bundle_yaml"] == ""
    assert [option["id"] for option in plan.output_updates["decision_options"]] == [
        "confirm_agreement",
        "adjust_agreement",
    ]
    assert plan.output_updates["decision_options"][0]["recommended"] is True
    assert plan.event_type == "alignment_agreement_ready"
    assert plan.event_payload == {
        "alignment_stage": "agreement_ready",
        "working_agreement": working_agreement,
    }


def test_alignment_agreement_readiness_checklist_issues_ignore_confirmation_gate() -> None:
    readiness_keys = ["loop_fit", "task_scope", "explicit_confirmation"]

    assert alignment_agreement_readiness_checklist_issues(["bad"], readiness_keys=readiness_keys) == [
        "readiness_checklist"
    ]
    assert alignment_agreement_readiness_checklist_issues(
        {"loop_fit": True, "task_scope": False, "explicit_confirmation": False},
        readiness_keys=readiness_keys,
    ) == ["task_scope"]
