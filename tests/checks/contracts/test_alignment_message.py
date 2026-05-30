from pathlib import Path

import pytest

from loopora.service_alignment_message import AlignmentMessageContext, append_alignment_message
from loopora.service_alignment_transcript import AlignmentTranscriptContext
from loopora.service_types import LooporaConflictError, LooporaError


class FakeAlignmentMessageRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []
        self.updates: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.updates.append(fields)
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def message_context(repo: FakeAlignmentMessageRepository):
    started_sessions: list[str] = []

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def transcript_context() -> AlignmentTranscriptContext:
        return AlignmentTranscriptContext(repository=repo, get_session=get_session)

    def start_session_async(session_id: str) -> None:
        started_sessions.append(session_id)
        repo.session["status"] = "running"

    context = AlignmentMessageContext(
        get_session=get_session,
        transcript_context=transcript_context,
        start_session_async=start_session_async,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, started_sessions


def test_alignment_message_command_records_user_message_stage_event_and_starts(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_message" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentMessageRepository(
        {
            "id": "align_message",
            "status": "waiting_user",
            "alignment_stage": "agreement_ready",
            "bundle_path": str(bundle_path),
            "transcript": [{"role": "assistant", "content": "Confirm this agreement."}],
            "working_agreement": {"readiness_checklist": {"loop_fit": True}},
            "error_message": "previous validation problem",
            "stop_requested": True,
            "repair_attempts": 1,
            "finished_at": "earlier",
        }
    )
    context, started_sessions = message_context(repo)

    session = append_alignment_message(
        context,
        "align_message",
        "  确认，就这样继续。  ",
        active_statuses={"running", "validating", "repairing"},
        confirmed_stages={"confirmed", "compiling", "ready_review"},
    )

    assert session["status"] == "running"
    assert repo.session["alignment_stage"] == "confirmed"
    assert repo.session["error_message"] == ""
    assert repo.session["stop_requested"] is False
    assert repo.session["repair_attempts"] == 0
    assert repo.session["finished_at"] is None
    assert repo.session["working_agreement"]["confirmed_at"] == "2026-05-30T00:00:00Z"
    assert repo.session["working_agreement"]["confirmation_message"] == "确认，就这样继续。"
    assert repo.session["transcript"][-1] == {
        "role": "user",
        "content": "确认，就这样继续。",
        "created_at": "2026-05-30T00:00:00Z",
    }
    assert [event["event_type"] for event in repo.events] == [
        "alignment_user_message",
        "alignment_agreement_confirmed",
    ]
    assert started_sessions == ["align_message"]
    transcript_log = tmp_path / "align_message" / "conversation" / "transcript.jsonl"
    assert '"content": "确认，就这样继续。"' in transcript_log.read_text(encoding="utf-8")


def test_alignment_message_command_rejects_empty_and_active_sessions(tmp_path: Path) -> None:
    repo = FakeAlignmentMessageRepository(
        {
            "id": "align_message",
            "status": "idle",
            "alignment_stage": "clarifying",
            "bundle_path": str(tmp_path / "align_message" / "artifacts" / "bundle.yml"),
            "transcript": [],
        }
    )
    context, started_sessions = message_context(repo)

    with pytest.raises(LooporaError, match="message is required"):
        append_alignment_message(
            context,
            "align_message",
            "   ",
            active_statuses={"running"},
            confirmed_stages={"confirmed"},
        )

    repo.session["status"] = "running"
    with pytest.raises(LooporaConflictError, match="already running"):
        append_alignment_message(
            context,
            "align_message",
            "Continue.",
            active_statuses={"running"},
            confirmed_stages={"confirmed"},
        )

    assert started_sessions == []
    assert repo.events == []
