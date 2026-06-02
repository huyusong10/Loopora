from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_source_context import (
    alignment_transcript_source_summary,
    bounded_alignment_file_text,
    redact_alignment_source_value,
)


TRANSCRIPT_SOURCE_SUMMARY_LIMIT = 8


def test_redact_alignment_source_value_preserves_safe_structure() -> None:
    redacted = redact_alignment_source_value(
        {
            "source_type": "spec_file",
            "items": [{"label": "safe"}, {"password": "SOURCE_PASSWORD_SECRET"}],
        }
    )

    assert redacted == {
        "source_type": "spec_file",
        "items": [{"label": "safe"}, {"password": "<secret omitted>"}],
    }


def test_bounded_alignment_file_text_redacts_and_truncates(tmp_path: Path) -> None:
    source = tmp_path / "spec.md"
    source.write_text("Authorization: Bearer FILE_TEXT_TOKEN_SECRET\n" + ("x" * 80), encoding="utf-8")

    text = bounded_alignment_file_text(source, limit=40)

    assert "FILE_TEXT_TOKEN_SECRET" not in text
    assert "<secret omitted>" in text
    assert text.endswith("[Loopora truncated this source context for prompt size.]")


def test_alignment_transcript_source_summary_uses_recent_redacted_entries() -> None:
    session = {
        "transcript": [
            {"role": "user", "content": f"message {index}", "created_at": str(index)}
            for index in range(9)
        ]
        + [{"role": "assistant", "content": "Cookie: sid=TRANSCRIPT_COOKIE_SECRET", "created_at": "9"}]
    }

    summary = alignment_transcript_source_summary(session)
    rendered = str(summary)

    assert len(summary) == TRANSCRIPT_SOURCE_SUMMARY_LIMIT
    assert summary[0]["content"] == "message 2"
    assert "TRANSCRIPT_COOKIE_SECRET" not in rendered
    assert "<secret omitted>" in rendered
