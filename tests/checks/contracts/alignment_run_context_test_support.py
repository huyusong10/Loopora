from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_run_context import AlignmentRunContextResolverContext
from loopora.service_types import LooporaError


class FakeAlignmentRunContextRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]] | None = None) -> None:
        self.sessions = sessions
        self.events_by_session = events_by_session or {}

    def list_all_alignment_sessions(self) -> list[dict]:
        return self.sessions

    def list_alignment_events(self, session_id: str, *, limit: int = 200) -> list[dict]:
        return self.events_by_session.get(session_id, [])[:limit]


def same_workdir(left: object, right: object) -> bool:
    if not left or not right:
        return False
    return Path(str(left)).expanduser().resolve() == Path(str(right)).expanduser().resolve()


def missing_run(run_id: str) -> dict:
    raise LooporaError(f"missing run: {run_id}")


def empty_binding(_adapter: str, _root: Path, *, context_id: str = "") -> dict:
    assert isinstance(context_id, str)
    return {}


def resolver_context(
    repo: FakeAlignmentRunContextRepository,
    *,
    read_binding,
    get_alignment_session=None,
) -> AlignmentRunContextResolverContext:
    def default_get_alignment_session(session_id: str) -> dict:
        for session in repo.sessions:
            if session.get("id") == session_id:
                return dict(session)
        raise LooporaError(f"missing alignment session: {session_id}")

    return AlignmentRunContextResolverContext(
        repository=repo,
        get_alignment_session=get_alignment_session or default_get_alignment_session,
        get_run=missing_run,
        same_workdir=same_workdir,
        read_binding=read_binding,
    )
