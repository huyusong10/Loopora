from pathlib import Path

import pytest

from loopora.service_alignment_session_projection import (
    AlignmentSessionAccessContext,
    alignment_session_detail_projection,
    alignment_session_summary,
    decorate_alignment_session,
    get_alignment_session,
    latest_alignment_event_id,
    list_alignment_events,
    list_alignment_sessions,
)
from loopora.service_types import LooporaNotFoundError


class FakeAlignmentSessionProjectionRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]] | None = None) -> None:
        self.sessions = {str(session["id"]): dict(session) for session in sessions}
        self.events_by_session = events_by_session or {}
        self.list_limits: list[int] = []

    def get_alignment_session(self, session_id: str) -> dict | None:
        session = self.sessions.get(session_id)
        return dict(session) if session else None

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        self.list_limits.append(limit)
        return [dict(session) for session in self.sessions.values()][:limit]

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        return [
            dict(event)
            for event in self.events_by_session.get(session_id, [])
            if int(event.get("id") or 0) > int(after_id or 0)
        ][:limit]

    def latest_alignment_event_id(self, session_id: str) -> int:
        events = self.events_by_session.get(session_id, [])
        return max([int(event.get("id") or 0) for event in events], default=0)


def session_access_context(
    repo: FakeAlignmentSessionProjectionRepository,
    *,
    ensure_calls: list[str] | None = None,
) -> AlignmentSessionAccessContext:
    def ensure_session_layout(session: dict) -> dict:
        if ensure_calls is not None:
            ensure_calls.append(str(session["id"]))
        return {**session, "layout_checked": True}

    return AlignmentSessionAccessContext(
        repository=repo,
        ensure_session_layout=ensure_session_layout,
        candidate_event=lambda session_id: {
            "event_type": "agent_candidate_received",
            "payload": {
                "candidate_origin": "agent_entry",
                "requires_web_alignment": True,
                "requires_candidate_repair": False,
                "adapter": "codex",
                "entry_source": "codex_project_skill",
                "host_context_id": f"thread:{session_id}",
                "has_candidate_yaml": True,
            },
        },
        ready_event=lambda session_id: {"event_type": "ready", "payload": {"session_id": session_id}},
        active_statuses={"running"},
        missing_judgment_item_ids=["task_scope"],
    )


def test_decorate_alignment_session_projects_runtime_flags_and_defaults(tmp_path: Path) -> None:
    session = {
        "id": "align_1",
        "status": "running",
        "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
        "working_agreement": "invalid",
        "executor_session_ref": {"session_id": "native-session"},
    }

    decorated = decorate_alignment_session(session, active_statuses={"running", "repairing"})

    assert decorated["artifact_dir"] == str(tmp_path / "align_1")
    assert decorated["is_active"] is True
    assert decorated["is_ready"] is False
    assert decorated["alignment_stage"] == "clarifying"
    assert decorated["working_agreement"] == {}
    assert decorated["native_resume_available"] is True


def test_alignment_session_access_projects_detail_and_checks_layout(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionProjectionRepository(
        [
            {
                "id": "align_1",
                "status": "running",
                "workdir": str(tmp_path),
                "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
                "transcript": [{"role": "user", "content": "Plan from Agent entry."}],
                "working_agreement": {},
            }
        ]
    )
    ensure_calls: list[str] = []

    session = get_alignment_session(session_access_context(repo, ensure_calls=ensure_calls), "align_1")

    assert ensure_calls == ["align_1"]
    assert session["layout_checked"] is True
    assert session["is_active"] is True
    assert session["agent_entry_review"]["missing_judgment_item_ids"] == ["task_scope"]
    assert session["agent_entry_launch"]["source"] == "agent_entry"
    assert session["agent_entry_launch"]["host_context_id"] == "thread:align_1"


def test_alignment_session_access_lists_summaries_and_validates_event_reads(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionProjectionRepository(
        [
            {
                "id": "align_1",
                "status": "idle",
                "workdir": str(tmp_path),
                "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
                "transcript": [{"role": "user", "content": "Use Authorization: Bearer SESSION_ACCESS_SECRET"}],
            }
        ],
        events_by_session={
            "align_1": [
                {"id": 1, "event_type": "alignment_started", "payload": {}},
                {"id": 2, "event_type": "alignment_ready", "payload": {}},
            ]
        },
    )
    context = session_access_context(repo)

    summaries = list_alignment_sessions(context, limit=5)
    events = list_alignment_events(context, "align_1", after_id=1, limit=10)
    latest_id = latest_alignment_event_id(context, "align_1")

    assert repo.list_limits == [5]
    assert summaries[0]["title"] == "Use Authorization: <secret omitted>"
    assert events == [{"id": 2, "event_type": "alignment_ready", "payload": {}}]
    assert latest_id == 2

    with pytest.raises(LooporaNotFoundError, match="unknown alignment session"):
        list_alignment_events(context, "missing")


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
    assert summary["message_count"] == 3
    assert summary["native_resume_available"] is True
    assert "SESSION_SUMMARY_SECRET" not in rendered
    assert "SESSION_LAST_SECRET" not in rendered


def test_alignment_session_detail_projection_attaches_agent_entry_views(tmp_path: Path) -> None:
    session = {
        "id": "align_1",
        "status": "idle",
        "workdir": str(tmp_path),
        "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
        "transcript": [{"role": "user", "content": "Shape this Loop from the Agent entry."}],
        "executor_kind": "codex",
        "working_agreement": {},
    }
    candidate_event = {
        "event_type": "agent_candidate_received",
        "payload": {
            "candidate_origin": "agent_entry",
            "requires_web_alignment": True,
            "requires_candidate_repair": True,
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "host_context_id": "thread-a",
            "source_path": str(tmp_path / "loopora-plan.yml"),
            "has_candidate_yaml": True,
            "candidate_sha256": "candidate-sha",
            "candidate_bytes": 42,
        },
    }
    ready_event = {
        "event_type": "agent_candidate_ready_content",
        "payload": {
            "candidate_origin": "agent_entry",
            "ready_candidate_sha256": "ready-sha",
            "ready_candidate_bytes": 84,
        },
    }

    detail = alignment_session_detail_projection(
        session,
        active_statuses={"running"},
        candidate_event=candidate_event,
        ready_event=ready_event,
        missing_judgment_item_ids=["task_scope"],
    )

    assert detail["agent_entry_review"]["source"] == "agent_entry"
    assert detail["agent_entry_review"]["missing_judgment_item_ids"] == ["task_scope"]
    assert detail["agent_entry_review"]["task_message"] == "Shape this Loop from the Agent entry."
    assert detail["agent_entry_launch"]["source"] == "agent_entry"
    assert detail["agent_entry_launch"]["slash_command"] == "/loopora-run"
    assert detail["agent_entry_launch"]["host_context_id"] == "thread-a"
    assert detail["agent_entry_launch"]["ready_candidate_sha256"] == "ready-sha"
    assert detail["agent_entry_launch"]["ready_candidate_bytes"] == 84
