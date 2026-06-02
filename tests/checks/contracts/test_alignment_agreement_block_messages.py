from __future__ import annotations

from loopora.service_alignment_stage import (
    AlignmentAgreementBlockCandidate,
    alignment_agreement_block_plan,
    alignment_block_message,
)


def test_alignment_agreement_block_plan_selects_first_issue_group() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=[],
                event_type="alignment_checklist_incomplete",
                fallback_message="缺少：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["loop_fit", "task_scope"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["agreement_summary"],
                event_type="alignment_language_mismatch",
                fallback_message="缺少语言：{missing}",
            ),
        ],
        prefers_chinese=True,
    )

    assert plan is not None
    assert plan.event_type == "alignment_evidence_incomplete"
    assert plan.event_payload == {
        "alignment_stage": "clarifying",
        "missing": ["loop_fit", "task_scope"],
    }
    assert plan.output_updates == {
        "alignment_phase": "clarifying",
        "agreement_summary": "",
        "bundle_yaml": "",
        "needs_user_input": True,
        "alignment_missing_items": ["loop_fit", "task_scope"],
        "assistant_message": "缺少证据：loop_fit, task_scope",
    }


def test_alignment_agreement_block_plan_uses_event_semantics_for_english_messages() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["readiness_evidence"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少：{missing}",
            ),
        ],
        prefers_chinese=False,
    )

    assert plan is not None
    assert "readiness evidence is not specific enough: readiness_evidence" in plan.output_updates["assistant_message"]


def test_alignment_agreement_block_plan_returns_none_without_issues() -> None:
    assert (
        alignment_agreement_block_plan(
            [
                AlignmentAgreementBlockCandidate(
                    issues=[],
                    event_type="alignment_checklist_incomplete",
                    fallback_message="缺少：{missing}",
                ),
            ],
            prefers_chinese=True,
        )
        is None
    )


def test_alignment_block_message_uses_language_and_event_semantics() -> None:
    assert (
        alignment_block_message(
            prefers_chinese=True,
            event_type="alignment_evidence_incomplete",
            missing=["loop_fit"],
            fallback_zh="缺少：{missing}",
        )
        == "缺少：loop_fit"
    )

    evidence_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_evidence_incomplete",
        missing=["loop_fit"],
        fallback_zh="缺少：{missing}",
    )
    language_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_language_mismatch",
        missing=["agreement_summary"],
        fallback_zh="缺少：{missing}",
    )

    assert "readiness evidence is not specific enough: loop_fit" in evidence_message
    assert "user-facing agreement fields need the user's language: agreement_summary" in language_message
