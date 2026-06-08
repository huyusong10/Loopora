from __future__ import annotations

from loopora.service_alignment_stage import alignment_output_message_plan


def test_alignment_output_message_plan_preserves_bundle_and_missing_items() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "已整理成 bundle。",
            "bundle_yaml": "version: 1\n",
        },
        stage_error="",
        missing_items=["task_scope"],
        prefers_chinese=True,
    )

    assert plan.assistant_message == "已整理成 bundle。"
    assert plan.bundle_yaml == "version: 1"
    assert plan.missing_items == ["task_scope"]
    assert plan.has_bundle_for_options is True
    assert plan.event_type == ""
    assert plan.use_default_decision_options is False


def test_alignment_output_message_plan_rewrites_non_chinese_assistant_message() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "I prepared a follow-up question.",
            "needs_user_input": True,
        },
        stage_error="",
        missing_items=["loop_fit"],
        prefers_chinese=True,
    )

    assert "确认一个会改变 Loop 形状的点" in plan.assistant_message
    assert plan.bundle_yaml == ""
    assert plan.missing_items == ["loop_fit"]
    assert plan.has_bundle_for_options is False
    assert plan.event_type == "alignment_language_mismatch"
    assert plan.event_payload == {"missing": ["assistant_message"], "surface": "assistant_message"}
    assert plan.use_default_decision_options is True
    assert plan.force_needs_user_input is False


def test_alignment_output_message_plan_blocks_stage_error_before_bundle_handling() -> None:
    plan = alignment_output_message_plan(
        {
            "assistant_message": "已整理完成。",
            "bundle_yaml": "version: 1\n",
        },
        stage_error="需要先确认协议。",
        stage_missing_items=["agreement_summary"],
        missing_items=["agreement_summary"],
        prefers_chinese=True,
    )

    assert plan.assistant_message == "需要先确认协议。"
    assert plan.bundle_yaml == ""
    assert plan.missing_items is None
    assert plan.has_bundle_for_options is False
    assert plan.event_type == "alignment_stage_blocked"
    assert plan.event_payload == {"status": "waiting_user", "error": "需要先确认协议。", "missing": ["agreement_summary"]}
    assert plan.force_needs_user_input is True
    assert plan.use_default_decision_options is True
