from __future__ import annotations

from collections.abc import Callable

from loopora.service_alignment_revision import AlignmentRevisionContext
from loopora.service_alignment_source_seed import redact_alignment_source_value


class FakeAlignmentRevisionRepository:
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


def revision_context(
    repo: FakeAlignmentRevisionRepository,
    *,
    write_transcript_log: Callable[[dict], None] | None = None,
):
    created_sessions: list[dict] = []
    started_sessions: list[str] = []
    logged_sessions: list[dict] = []

    def create_session(**fields: object) -> dict:
        created_sessions.append(dict(fields))
        return dict(repo.session)

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def start_session_async(session_id: str) -> None:
        started_sessions.append(session_id)
        repo.session["status"] = "running"

    context = AlignmentRevisionContext(
        repository=repo,
        create_session=create_session,
        get_session=get_session,
        export_bundle=lambda _bundle_id: {},
        get_run=lambda _run_id: {},
        get_loop=lambda _loop_id: {},
        run_source_bundle=lambda _run, _loop: ("", {}),
        start_session_async=start_session_async,
        redact_source_value=redact_alignment_source_value,
        write_transcript_log=write_transcript_log or (lambda session: logged_sessions.append(dict(session))),
    )
    return context, created_sessions, started_sessions, logged_sessions
