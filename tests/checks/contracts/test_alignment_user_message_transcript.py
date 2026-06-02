from __future__ import annotations

from pathlib import Path

from alignment_transcript_test_support import FakeAlignmentTranscriptRepository, transcript_context
from loopora.service_alignment_transcript import AlignmentUserMessageEffect, apply_alignment_user_message


def test_alignment_user_message_effect_appends_transcript_events_and_artifact(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_1" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentTranscriptRepository(
        {
            "id": "align_1",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "assistant", "content": "What should I optimize?"}],
            "error_message": "previous failure",
            "stop_requested": True,
            "repair_attempts": 2,
            "finished_at": "earlier",
        }
    )

    updated = apply_alignment_user_message(
        transcript_context(repo),
        "align_1",
        AlignmentUserMessageEffect(
            session=repo.session,
            message="Optimize the alignment transcript boundary.",
            created_at="2026-05-29T00:00:00Z",
            update_fields={"alignment_stage": "agreement_confirmed"},
            stage_event_type="alignment_agreement_confirmed",
            stage_event_payload={"alignment_stage": "agreement_confirmed"},
        ),
    )

    assert updated["error_message"] == ""
    assert updated["stop_requested"] is False
    assert updated["repair_attempts"] == 0
    assert updated["finished_at"] is None
    assert updated["alignment_stage"] == "agreement_confirmed"
    assert updated["transcript"][-1] == {
        "role": "user",
        "content": "Optimize the alignment transcript boundary.",
        "created_at": "2026-05-29T00:00:00Z",
    }
    assert [event["event_type"] for event in repo.events] == [
        "alignment_user_message",
        "alignment_agreement_confirmed",
    ]
    transcript_log = tmp_path / "align_1" / "conversation" / "transcript.jsonl"
    assert '"content": "Optimize the alignment transcript boundary."' in transcript_log.read_text(encoding="utf-8")
