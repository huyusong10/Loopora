from __future__ import annotations

from pathlib import Path

from alignment_transcript_test_support import FakeAlignmentTranscriptRepository, transcript_context
from loopora.service_alignment_transcript import alignment_notice_appender, append_alignment_notice_message


def test_alignment_notice_message_appends_provided_content(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_notice" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_notice",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "user", "content": "Please continue."}],
        }
    )

    updated = append_alignment_notice_message(
        transcript_context(repo),
        "align_notice",
        content="Reloaded bundle.yml.",
        created_at="2026-05-29T00:04:00Z",
    )

    assert updated["transcript"][-1] == {
        "role": "assistant",
        "content": "Reloaded bundle.yml.",
        "created_at": "2026-05-29T00:04:00Z",
    }


def test_alignment_notice_appender_uses_current_time(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_notice_clock" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_notice_clock",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "user", "content": "Please continue."}],
        }
    )
    append_notice = alignment_notice_appender(
        transcript_context(repo),
        now=lambda: "2026-05-29T00:05:00Z",
    )

    updated = append_notice("align_notice_clock", "Reloaded bundle.yml.")

    assert updated["transcript"][-1] == {
        "role": "assistant",
        "content": "Reloaded bundle.yml.",
        "created_at": "2026-05-29T00:05:00Z",
    }
