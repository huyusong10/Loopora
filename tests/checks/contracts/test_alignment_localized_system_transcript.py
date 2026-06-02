from __future__ import annotations

from pathlib import Path

from alignment_transcript_test_support import FakeAlignmentTranscriptRepository, transcript_context
from loopora.service_alignment_transcript import (
    append_localized_alignment_system_message,
    localized_alignment_system_message_appender,
)


def test_localized_alignment_system_message_uses_session_language(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_zh" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_zh",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "user", "content": "请继续整理这个 Loop。"}],
        }
    )

    updated = append_localized_alignment_system_message(
        transcript_context(repo),
        "align_zh",
        zh="已重新读取 bundle.yml。",
        en="Reloaded bundle.yml.",
        created_at="2026-05-29T00:03:00Z",
    )

    assert updated["transcript"][-1]["content"] == "已重新读取 bundle.yml。"

    repo.session["id"] = "align_en"
    repo.session["bundle_path"] = str(tmp_path / "align_en" / "artifacts" / "bundle.yml")
    repo.session["transcript"] = [{"role": "user", "content": "Please continue."}]

    updated = append_localized_alignment_system_message(
        transcript_context(repo),
        "align_en",
        zh="已重新读取 bundle.yml。",
        en="Reloaded bundle.yml.",
        created_at="2026-05-29T00:04:00Z",
    )

    assert updated["transcript"][-1]["content"] == "Reloaded bundle.yml."


def test_localized_alignment_system_message_appender_uses_current_time(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_system" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_system",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "user", "content": "Please continue."}],
        }
    )
    append_system_message = localized_alignment_system_message_appender(
        transcript_context(repo),
        now=lambda: "2026-05-29T00:05:00Z",
    )

    updated = append_system_message(
        "align_system",
        zh="已重新读取 bundle.yml。",
        en="Reloaded bundle.yml.",
    )

    assert updated["transcript"][-1] == {
        "role": "assistant",
        "content": "Reloaded bundle.yml.",
        "created_at": "2026-05-29T00:05:00Z",
    }
