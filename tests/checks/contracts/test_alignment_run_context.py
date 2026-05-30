from pathlib import Path

from loopora.service_alignment_run_context import (
    AlignmentRunContextResolverContext,
    resolve_alignment_run_context,
)
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
    _ = context_id
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


def test_alignment_run_context_resolver_reports_plan_first_when_no_binding_or_recovery(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository([])

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=empty_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-empty",
    )

    assert result["action"] == "plan_first"
    assert result["confidence"] == "no_binding"
    assert result["requires_user_choice"] is False
    assert result["choices"] == []
    assert result["context_id"] == "thread-empty"


def test_alignment_run_context_resolver_reports_damaged_binding_before_recovery(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path)}],
        events_by_session={
            "align_1": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {
                        "candidate_origin": "agent_entry",
                        "adapter": "codex",
                        "has_candidate_yaml": True,
                    },
                }
            ]
        },
    )

    def damaged_binding(_adapter: str, _root: Path, *, context_id: str = "") -> dict:
        _ = context_id
        raise LooporaError("binding json is unreadable")

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=damaged_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-broken",
    )

    assert result["action"] == "repair_agent_binding"
    assert result["confidence"] == "damaged_binding"
    assert "binding json is unreadable" in result["binding_error"]
    assert result["choices"] == []


def test_alignment_run_context_resolver_uses_exact_binding_without_user_choice(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path), "transcript": [{"role": "user", "content": "Ship it."}]}],
    )

    result = resolve_alignment_run_context(
        resolver_context(
            repo,
            read_binding=lambda _adapter, _root, *, context_id="": {
                "alignment_session_id": "align_1",
                "workdir": str(tmp_path),
                "host_context_id": context_id,
                "access_token": "SECRET",
            },
        ),
        tmp_path,
        adapter="codex",
        context_id="thread-a",
    )

    assert result["action"] == "start_ready_preview"
    assert result["confidence"] == "exact_binding"
    assert result["requires_user_choice"] is False
    assert result["alignment_session_id"] == "align_1"
    assert result["binding"]["host_context_id"] == "thread-a"
    assert "access_token" not in result["binding"]
    assert result["choice"]["alignment_session_id"] == "align_1"
    assert result["choice"]["action"] == "start_ready_preview"


def test_alignment_run_context_resolver_lists_recoverable_choices_when_binding_is_absent(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path), "transcript": [{"role": "user", "content": "Resume me."}]}],
        events_by_session={
            "align_1": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {
                        "candidate_origin": "agent_entry",
                        "adapter": "codex",
                        "entry_source": "codex_project_skill",
                        "host_context_id": "thread-a",
                        "has_candidate_yaml": True,
                    },
                }
            ]
        },
    )

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=empty_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-new",
    )

    assert result["action"] == "choose_recoverable_context"
    assert result["confidence"] == "single_recoverable"
    assert result["requires_user_choice"] is True
    assert result["choice_count"] == 1
    assert result["runnable_choice_count"] == 1
    assert result["choices"][0]["alignment_session_id"] == "align_1"
    assert result["choices"][0]["host_context_id"] == "thread-a"
