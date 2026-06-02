from __future__ import annotations

from loopora.service_alignment_stage import alignment_fallback_assistant_message


def test_alignment_stage_fallback_messages_preserve_semantic_paths() -> None:
    assert alignment_fallback_assistant_message(has_bundle=True, needs_user_input=False) == "已整理成一个可导入的 Loopora bundle。"
    assert "确认一个会改变 Loop 形状的点" in alignment_fallback_assistant_message(
        has_bundle=False,
        needs_user_input=True,
    )
    assert alignment_fallback_assistant_message(has_bundle=False, needs_user_input=False) == "我需要继续用中文对齐后再继续。"
