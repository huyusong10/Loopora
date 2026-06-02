from __future__ import annotations


class AgentRecoveryRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]], *, expose_all_sessions: bool = True):
        self.sessions = sessions
        self.events_by_session = events_by_session
        self.expose_all_sessions = expose_all_sessions
        self.used_all_sessions = False
        self.list_sessions_limits: list[int] = []
        self.event_limits: list[tuple[str, int]] = []

    def list_all_alignment_sessions(self) -> list[dict]:
        if not self.expose_all_sessions:
            raise AttributeError("list_all_alignment_sessions disabled for this test")
        self.used_all_sessions = True
        return self.sessions

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_sessions_limits.append(limit)
        return self.sessions[:limit]

    def list_alignment_events(self, session_id: str, *, limit: int = 200) -> list[dict]:
        self.event_limits.append((session_id, limit))
        return self.events_by_session.get(session_id, [])[:limit]


class FallbackAgentRecoveryRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]]):
        self.sessions = sessions
        self.events_by_session = events_by_session
        self.list_sessions_limits: list[int] = []

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_sessions_limits.append(limit)
        return self.sessions[:limit]

    def list_alignment_events(self, session_id: str, *, limit: int = 200) -> list[dict]:
        return self.events_by_session.get(session_id, [])[:limit]
