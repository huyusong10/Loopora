from pathlib import Path

import pytest

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_requests import AlignmentSessionCreateRequest
from loopora.service_alignment_session_creation import AlignmentSessionCreationContext, alignment_session_dir, create_alignment_session
from loopora.service_types import LooporaError


class FakeAlignmentSessionCreationRepository:
    def __init__(self) -> None:
        self.session: dict = {}
        self.events: list[dict] = []

    def create_alignment_session(self, payload: dict) -> dict:
        self.session = dict(payload)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def creation_context(repo: FakeAlignmentSessionCreationRepository, *, source_seed: dict | None = None):
    started_sessions: list[str] = []
    logged_sessions: list[dict] = []
    resolved_sources: list[dict] = []

    def resolve_source_seed(workdir: Path, source_option_id: str) -> dict:
        resolved_sources.append({"workdir": str(workdir), "source_option_id": source_option_id})
        return dict(source_seed or {})

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def start_session_async(session_id: str) -> None:
        started_sessions.append(session_id)
        repo.session["status"] = "running"

    context = AlignmentSessionCreationContext(
        repository=repo,
        resolve_source_seed=resolve_source_seed,
        session_dir=alignment_session_dir,
        ensure_artifact_dirs=lambda root: (root / "artifacts").mkdir(parents=True, exist_ok=True),
        get_session=get_session,
        start_session_async=start_session_async,
        write_transcript_log=lambda session: logged_sessions.append(dict(session)),
        id_factory=lambda prefix: f"{prefix}_fixed",
        now=lambda: "2026-05-29T00:00:00Z",
    )
    return context, started_sessions, logged_sessions, resolved_sources


def test_alignment_session_creation_records_seeded_session_events_and_starts_after_transcript_log(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))
    context, started_sessions, logged_sessions, resolved_sources = creation_context(
        repo,
        source_seed={
            "working_agreement": {"mode": "improvement"},
            "linked_bundle_id": "bundle_1",
            "linked_loop_id": "loop_1",
            "linked_run_id": "run_1",
            "seed_bundle": seed_bundle,
            "event": {"source_type": "bundle", "source_bundle_id": "bundle_1"},
        },
    )

    session = create_alignment_session(
        context,
        AlignmentSessionCreateRequest(
            workdir=tmp_path,
            message="  Shape this task into a Loop.  ",
            source_option_id="bundle:bundle_1",
            start_immediately=True,
        ),
    )

    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_fixed" / "artifacts" / "bundle.yml"
    assert session["status"] == "running"
    assert repo.session["id"] == "align_fixed"
    assert repo.session["workdir"] == str(tmp_path.resolve())
    assert repo.session["bundle_path"] == str(bundle_path)
    assert repo.session["transcript"] == [
        {"role": "user", "content": "Shape this task into a Loop.", "created_at": "2026-05-29T00:00:00Z"}
    ]
    assert repo.session["working_agreement"] == {"mode": "improvement"}
    assert repo.session["linked_bundle_id"] == "bundle_1"
    assert repo.session["linked_loop_id"] == "loop_1"
    assert repo.session["linked_run_id"] == "run_1"
    assert bundle_path.exists()
    assert "Ship the focused starter experience" in bundle_path.read_text(encoding="utf-8")
    assert repo.events == [
        {
            "event_type": "alignment_session_created",
            "payload": {"status": "idle", "workdir": str(tmp_path.resolve()), "executor_kind": "codex"},
        },
        {
            "event_type": "alignment_source_context_selected",
            "payload": {"source_type": "bundle", "source_bundle_id": "bundle_1"},
        },
    ]
    assert logged_sessions[0]["status"] == "idle"
    assert started_sessions == ["align_fixed"]
    assert resolved_sources == [{"workdir": str(tmp_path.resolve()), "source_option_id": "bundle:bundle_1"}]


def test_alignment_session_creation_does_not_start_without_user_message(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    context, started_sessions, logged_sessions, _resolved_sources = creation_context(repo)

    session = create_alignment_session(
        context,
        AlignmentSessionCreateRequest(workdir=tmp_path, message="", start_immediately=True),
    )

    assert session["status"] == "idle"
    assert repo.session["transcript"] == []
    assert started_sessions == []
    assert logged_sessions[0]["id"] == "align_fixed"


def test_alignment_session_creation_rejects_missing_workdir(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    context, _started_sessions, _logged_sessions, _resolved_sources = creation_context(repo)

    with pytest.raises(LooporaError, match="workdir does not exist"):
        create_alignment_session(context, AlignmentSessionCreateRequest(workdir=tmp_path / "missing"))
