from __future__ import annotations

from loopora.service_alignment_clarifying_questions import alignment_clarifying_question_issues


def test_alignment_clarifying_question_rewrite_requires_boolean_need() -> None:
    non_boolean_issues = alignment_clarifying_question_issues(
        {
            "needs_user_input": "true",
            "assistant_message": "What roles do you want?",
            "decision_options": [],
        }
    )
    boolean_issues = alignment_clarifying_question_issues(
        {
            "needs_user_input": True,
            "assistant_message": "What roles do you want?",
            "decision_options": [],
        }
    )

    assert non_boolean_issues == []
    assert "generic_alignment_question" in boolean_issues


def test_alignment_clarifying_question_rejects_internal_alignment_terms() -> None:
    issues = alignment_clarifying_question_issues(
        {
            "needs_user_input": True,
            "assistant_message": "These alignment fields are missing: readiness_evidence and evidence buckets.",
            "decision_options": [{"id": "recommended", "label": "Recommended", "recommended": True}],
        }
    )

    assert "internal_alignment_term_question" in issues
