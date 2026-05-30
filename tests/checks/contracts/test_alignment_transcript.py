from pathlib import Path

from loopora.service_alignment_transcript import (
    AlignmentAssistantMessageEffect,
    AlignmentTranscriptContext,
    AlignmentUserMessageEffect,
    append_alignment_system_message,
    append_localized_alignment_system_message,
    apply_alignment_user_message,
    localized_alignment_system_message_appender,
    record_alignment_assistant_message,
)


class FakeAlignmentTranscriptRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def transcript_context(repo: FakeAlignmentTranscriptRepository) -> AlignmentTranscriptContext:
    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    return AlignmentTranscriptContext(repository=repo, get_session=get_session)


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


def test_alignment_assistant_and_system_message_effects_update_transcript_and_artifact(tmp_path: Path) -> None:
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
    updated = append_alignment_system_message(
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
