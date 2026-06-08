from __future__ import annotations

from pathlib import Path

from alignment_transcript_test_support import FakeAlignmentTranscriptRepository, transcript_context
from loopora.service_alignment_transcript import (
    AlignmentAssistantMessageEffect,
    append_alignment_notice_message,
    record_alignment_assistant_message,
)


def test_alignment_assistant_and_notice_message_effects_update_transcript_and_artifact(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_1" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_1",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "user", "content": "Continue."}],
        }
    )
    context = transcript_context(repo)

    record_alignment_assistant_message(
        context,
        "align_1",
        AlignmentAssistantMessageEffect(
            session=repo.session,
            message="Choose the next extraction target.",
            created_at="2026-05-29T00:01:00Z",
            decision_options=[
                {
                    "id": "run_context",
                    "label": "Run context",
                    "description": "Extract run-context resolution.",
                    "recommended": True,
                    "user_reply": "Extract run-context resolution.",
                }
            ],
            missing_items=["run_context_boundary"],
        ),
    )
    updated = append_alignment_notice_message(
        context,
        "align_1",
        content="Failed to reload bundle.yml: invalid YAML",
        created_at="2026-05-29T00:02:00Z",
    )

    assert updated["transcript"][-2]["decision_options"][0]["id"] == "run_context"
    assert updated["transcript"][-2]["missing_items"] == ["run_context_boundary"]
    assert updated["transcript"][-1] == {
        "role": "assistant",
        "content": "Failed to reload bundle.yml: invalid YAML",
        "created_at": "2026-05-29T00:02:00Z",
    }
    assert [event["event_type"] for event in repo.events] == ["alignment_message"]
    transcript_log = tmp_path / "align_1" / "conversation" / "transcript.jsonl"
    transcript_text = transcript_log.read_text(encoding="utf-8")
    assert '"missing_items": ["run_context_boundary"]' in transcript_text
    assert '"content": "Failed to reload bundle.yml: invalid YAML"' in transcript_text
