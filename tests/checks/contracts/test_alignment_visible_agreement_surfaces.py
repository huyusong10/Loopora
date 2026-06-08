from __future__ import annotations

from loopora.service_alignment_agreement_stage import (
    alignment_agreement_text_snippet,
    alignment_message_confirms_agreement,
    alignment_visible_agreement_message,
)


def test_alignment_visible_agreement_message_projects_english_confirmation_surface() -> None:
    message = alignment_visible_agreement_message(
        {
            "summary": "Confirmed direction.",
            "readiness_evidence": {
                "loop_fit": "Later rounds need new evidence.",
                "workflow_shape": "Builder, Inspector, GateKeeper.",
                "workdir_facts": "AGENTS.md exists.",
            },
        },
        prefers_chinese=False,
    )

    assert message.startswith("Please confirm this working agreement.")
    assert "Summary: Confirmed direction." in message
    assert "Loopora fit: Later rounds need new evidence." in message
    assert "Run-flow shape: Builder, Inspector, GateKeeper." in message
    assert "Workflow shape:" not in message
    assert "Project facts: AGENTS.md exists." in message


def test_alignment_visible_agreement_message_projects_chinese_confirmation_surface() -> None:
    message = alignment_visible_agreement_message(
        {
            "summary": "已确认方向。",
            "readiness_evidence": {
                "loop_fit": "后续轮次需要新证据。",
                "workflow_shape": "Builder 到 GateKeeper。",
                "workdir_facts": "存在 AGENTS.md。",
            },
        },
        prefers_chinese=True,
    )

    assert message.startswith("请先确认这份工作协议。")
    assert "摘要：已确认方向。" in message
    assert "为什么用 Loopora：后续轮次需要新证据。" in message
    assert "运行流程形状：Builder 到 GateKeeper。" in message
    assert "workflow 形状：" not in message
    assert "项目事实：存在 AGENTS.md。" in message


def test_alignment_agreement_text_snippet_collapses_space_and_truncates() -> None:
    assert alignment_agreement_text_snippet("  a   b\nc  ", limit=20) == "a b c"
    assert alignment_agreement_text_snippet("abcdef", limit=4) == "abc…"


def test_alignment_message_confirmation_allows_no_change_clause() -> None:
    assert alignment_message_confirms_agreement("可以，不需要修改，继续。") is True
    assert alignment_message_confirms_agreement("可以，但是不需要修改，继续。") is True
    assert alignment_message_confirms_agreement("确认，采用这份调整后的工作协议。") is True
    assert alignment_message_confirms_agreement("同意采用调整后的方案。") is True
    assert alignment_message_confirms_agreement("Approved, no changes, proceed.") is True


def test_alignment_message_confirmation_treats_requested_changes_as_adjustments() -> None:
    assert alignment_message_confirms_agreement("可以，但把证据偏好改成浏览器截图和命令输出。") is False
    assert alignment_message_confirms_agreement("Looks good, but add a stricter proof gate.") is False
    assert alignment_message_confirms_agreement("no") is False
