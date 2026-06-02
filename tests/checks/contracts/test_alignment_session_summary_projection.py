from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_session_projection import alignment_session_summary


ALIGNMENT_SUMMARY_MESSAGE_COUNT = 3


def test_alignment_session_summary_redacts_transcript_previews(tmp_path: Path) -> None:
    summary = alignment_session_summary(
        {
            "id": "align_secret",
            "status": "idle",
            "workdir": str(tmp_path),
            "bundle_path": str(tmp_path / "align_secret" / "artifacts" / "bundle.yml"),
            "transcript": [
                {"role": "assistant", "content": "Ignore this."},
                {"role": "user", "content": "Use Authorization: Bearer SESSION_SUMMARY_SECRET"},
                {"role": "assistant", "content": "Cookie: sid=SESSION_LAST_SECRET"},
            ],
            "executor_session_ref": {"session_id": "native-session"},
        },
        active_statuses={"running"},
    )
    rendered = str(summary)

    assert summary["title"] == "Use Authorization: <secret omitted>"
    assert summary["last_message"] == "Cookie: <secret omitted>"
    assert summary["message_count"] == ALIGNMENT_SUMMARY_MESSAGE_COUNT
    assert summary["native_resume_available"] is True
    assert "SESSION_SUMMARY_SECRET" not in rendered
    assert "SESSION_LAST_SECRET" not in rendered
