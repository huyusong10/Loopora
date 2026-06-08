from __future__ import annotations

from loopora.service_alignment_language import (
    alignment_generation_display_language,
    alignment_generation_prefers_chinese,
    alignment_prefers_chinese,
    alignment_user_language_hint,
)


def test_alignment_language_projection_ignores_neutral_confirmations_and_preserves_ready_review_language() -> None:
    neutral_confirmation = {
        "alignment_stage": "clarifying",
        "transcript": [
            {"role": "user", "content": "OK"},
            {"role": "user", "content": "请继续整理证据。"},
        ],
    }
    ready_review = {
        "alignment_stage": "ready_review",
        "transcript": [{"role": "user", "content": "Please improve this Loop."}],
        "working_agreement": {
            "summary": "继续保留中文预览。",
            "readiness_evidence": {"task_scope": "中文证据"},
        },
    }

    assert alignment_prefers_chinese(neutral_confirmation) is True
    assert alignment_generation_prefers_chinese(ready_review) is True
    assert alignment_user_language_hint(ready_review).startswith("Preserve the existing READY preview")
    assert "dominant substantive language" in alignment_user_language_hint(ready_review)
    assert "Chinese" not in alignment_user_language_hint(ready_review)
    assert alignment_user_language_hint({"transcript": [{"role": "user", "content": "Please continue."}]}).startswith(
        "Follow the dominant substantive task language"
    )


def test_ready_review_display_language_uses_source_agreement_not_new_feedback_language() -> None:
    ready_review = {
        "alignment_stage": "ready",
        "status": "ready",
        "transcript": [{"role": "user", "content": "请根据审查反馈继续加强证据。"}],
        "working_agreement": {
            "summary": "Keep the English READY preview language.",
            "readiness_evidence": {"task_scope": "English task evidence."},
        },
    }

    assert alignment_generation_prefers_chinese(ready_review) is False
    assert alignment_generation_display_language(ready_review) == ""
