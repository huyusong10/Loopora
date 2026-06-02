from __future__ import annotations

from loopora.service_alignment_agreement_stage import alignment_user_message_stage_plan


def test_alignment_user_message_stage_plan_confirms_agreement() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "agreement_ready",
            "status": "waiting_user",
            "working_agreement": {"readiness_checklist": {"loop_fit": True}},
        },
        "确认，就这样继续。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "confirmed"
    assert agreement["readiness_checklist"]["explicit_confirmation"] is True
    assert agreement["confirmed_at"] == "2026-05-29T00:00:00Z"
    assert agreement["confirmation_message"] == "确认，就这样继续。"
    assert plan.event_type == "alignment_agreement_confirmed"
    assert plan.event_payload == {"alignment_stage": "confirmed"}


def test_alignment_user_message_stage_plan_reopens_agreement_for_adjustment() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "agreement_ready",
            "status": "waiting_user",
            "working_agreement": {
                "readiness_checklist": {"loop_fit": True, "explicit_confirmation": True},
                "confirmed_at": "old",
                "confirmation_message": "old",
            },
        },
        "先别确认，把证据偏好调整成命令输出优先。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "clarifying"
    assert agreement["readiness_checklist"]["explicit_confirmation"] is False
    assert agreement["confirmed_at"] == ""
    assert agreement["confirmation_message"] == ""
    assert plan.event_type == "alignment_agreement_reopened"
    assert plan.event_payload == {"alignment_stage": "clarifying"}


def test_alignment_user_message_stage_plan_starts_ready_review() -> None:
    plan = alignment_user_message_stage_plan(
        {
            "alignment_stage": "ready",
            "status": "ready",
            "bundle_path": "/tmp/alignment.yaml",
            "working_agreement": {"summary": "Confirmed direction."},
        },
        "请按当前 bundle 再审查一次证据边界。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    agreement = plan.update_fields["working_agreement"]

    assert plan.update_fields["alignment_stage"] == "ready_review"
    assert agreement["ready_review"] == {
        "feedback": "请按当前 bundle 再审查一次证据边界。",
        "requested_at": "2026-05-29T00:00:00Z",
        "source_status": "ready",
    }
    assert plan.event_type == "alignment_ready_review_started"
    assert plan.event_payload == {
        "alignment_stage": "ready_review",
        "feedback": "请按当前 bundle 再审查一次证据边界。",
        "bundle_path": "/tmp/alignment.yaml",
    }


def test_alignment_user_message_stage_plan_reopens_unconfirmed_failed_session() -> None:
    plan = alignment_user_message_stage_plan(
        {"alignment_stage": "clarifying", "status": "failed"},
        "继续补齐。",
        captured_at="2026-05-29T00:00:00Z",
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert plan.event_type == ""
    assert plan.event_payload is None
