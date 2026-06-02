from __future__ import annotations

from loopora.service_alignment_language import (
    alignment_agreement_language_issues,
    alignment_assistant_message_language_issue,
    alignment_bundle_language_issues,
)


def test_alignment_agreement_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert (
        alignment_agreement_language_issues(
            {
                "agreement_summary": "English agreement.",
                "readiness_evidence": {"loop_fit": "English evidence."},
            },
            evidence_keys=["loop_fit"],
            prefers_chinese=False,
        )
        == []
    )


def test_alignment_agreement_language_issues_report_user_visible_non_chinese_fields() -> None:
    assert alignment_agreement_language_issues(
        {
            "agreement_summary": "English agreement.",
            "readiness_evidence": {
                "loop_fit": "需要持续证据。",
                "task_scope": "English scope.",
            },
        },
        evidence_keys=["loop_fit", "task_scope"],
        prefers_chinese=True,
    ) == ["agreement_summary", "task_scope"]


def test_alignment_agreement_language_issues_fail_closed_for_missing_evidence() -> None:
    assert alignment_agreement_language_issues(
        {"agreement_summary": "协议已经明确。", "readiness_evidence": ["bad"]},
        evidence_keys=["loop_fit"],
        prefers_chinese=True,
    ) == ["readiness_evidence"]


def test_alignment_bundle_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert alignment_bundle_language_issues({"collaboration_summary": "English summary."}, prefers_chinese=False) == []


def test_alignment_bundle_language_issues_report_non_chinese_bundle_surfaces() -> None:
    issues = alignment_bundle_language_issues(
        {
            "metadata": {"name": "Starter", "description": "English description."},
            "loop": {"name": "Starter Loop"},
            "collaboration_summary": "English collaboration summary.",
            "spec": {"markdown": "中文 spec。"},
            "workflow": {"collaboration_intent": "中文 workflow。"},
            "role_definitions": [
                {
                    "key": "builder",
                    "name": "Builder",
                    "description": "中文描述。",
                    "prompt_markdown": "English prompt.",
                    "posture_notes": "中文姿态。",
                }
            ],
        },
        prefers_chinese=True,
    )

    assert issues == [
        "bundle field metadata.name must follow Chinese user language",
        "bundle field metadata.description must follow Chinese user language",
        "bundle field loop.name must follow Chinese user language",
        "bundle field collaboration_summary must follow Chinese user language",
        "bundle role_definition builder.name must follow Chinese user language",
        "bundle role_definition builder.prompt_markdown must follow Chinese user language",
    ]


def test_alignment_assistant_message_language_issue_tracks_chinese_preference() -> None:
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=True) is True
    assert alignment_assistant_message_language_issue("已整理方案。", prefers_chinese=True) is False
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=False) is False
