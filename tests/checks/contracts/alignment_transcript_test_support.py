from __future__ import annotations

from loopora.service_alignment_transcript import AlignmentTranscriptContext


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
