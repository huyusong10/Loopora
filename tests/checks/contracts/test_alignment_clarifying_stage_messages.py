from __future__ import annotations

from loopora.service_alignment_stage import alignment_clarifying_reframe_message, alignment_clarifying_stage_plan


def test_alignment_clarifying_reframe_message_preserves_recommended_default() -> None:
    assert "优先阻断" in alignment_clarifying_reframe_message(prefers_chinese=True)
    assert "block results that look done but lack evidence" in alignment_clarifying_reframe_message(prefers_chinese=False)


def test_alignment_clarifying_stage_plan_reframes_low_value_questions() -> None:
    plan = alignment_clarifying_stage_plan(
        {
            "needs_user_input": True,
            "assistant_message": "Configure workflow roles and parallel groups?",
            "decision_options": [],
            "bundle_yaml": "version: 1\n",
        },
        prefers_chinese=True,
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert "优先阻断" in plan.output_updates["assistant_message"]
    assert plan.output_updates["decision_options"][0]["recommended"] is True
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["bundle_yaml"] == ""
    assert plan.event_type == "alignment_question_reframed"
    assert plan.event_payload == {
        "alignment_stage": "clarifying",
        "issues": ["mechanical_configuration_question", "missing_recommended_decision_options"],
    }


def test_alignment_clarifying_stage_plan_preserves_acceptable_question_output() -> None:
    plan = alignment_clarifying_stage_plan(
        {"assistant_message": "Here is an update.", "needs_user_input": False},
        prefers_chinese=False,
    )

    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert plan.output_updates == {}
    assert plan.event_type == ""
    assert plan.event_payload is None
