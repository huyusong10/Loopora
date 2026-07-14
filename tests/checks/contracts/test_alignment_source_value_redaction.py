from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_source_context import (
    MODEL_VISIBLE_LOCAL_PATH_OMITTED,
    alignment_transcript_source_summary,
    bounded_alignment_file_text,
    redact_alignment_model_context_value,
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


def test_redact_alignment_model_context_value_omits_local_source_paths() -> None:
    redacted = redact_alignment_model_context_value(
        {
            "source_type": "spec_file",
            "spec_path": "/private/project/.loopora/spec.md",
            "source_bundle_path": "~/project/.loopora/alignment_sessions/align_1/artifacts/bundle.yml",
            "artifact_paths": {
                "spec": "/private/project/.loopora/spec.md",
                "run_contract": "contract/run_contract.json",
            },
            "transcript_summary": [{"content": "Cookie: sid=SOURCE_CONTEXT_COOKIE_SECRET"}],
        }
    )

    assert redacted["source_type"] == "spec_file"
    assert redacted["spec_path"] == MODEL_VISIBLE_LOCAL_PATH_OMITTED
    assert redacted["source_bundle_path"] == MODEL_VISIBLE_LOCAL_PATH_OMITTED
    assert redacted["artifact_paths"] == {
        "spec": MODEL_VISIBLE_LOCAL_PATH_OMITTED,
        "run_contract": "contract/run_contract.json",
    }
    assert "SOURCE_CONTEXT_COOKIE_SECRET" not in str(redacted)
    assert "<secret omitted>" in str(redacted)


def test_bounded_alignment_file_text_redacts_and_truncates(tmp_path: Path) -> None:
    source = tmp_path / "spec.md"
    source.write_text("Authorization: Bearer FILE_TEXT_TOKEN_SECRET\n" + ("x" * 80), encoding="utf-8")

    text = bounded_alignment_file_text(source, limit=40)

    assert "FILE_TEXT_TOKEN_SECRET" not in text
    assert "<secret omitted>" in text
    assert text.endswith("[Loopora truncated this source context for prompt size.]")


def test_bounded_alignment_file_text_redacts_low_level_read_errors(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "spec.md"
    local_path = tmp_path / "private" / "spec.md"
    source.write_text("# Existing Spec\n", encoding="utf-8")

    def fail_read_text(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    text = bounded_alignment_file_text(source)

    assert text == "Source file could not be read."
    assert str(local_path) not in text
    assert "permission denied" not in text


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
