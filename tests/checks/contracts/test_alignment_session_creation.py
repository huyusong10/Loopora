from collections.abc import Callable
from pathlib import Path

import pytest

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_requests import AlignmentSessionCreateRequest
from loopora.service_alignment_session_creation import (
    ALIGNMENT_SESSION_CREATE_ERROR,
    AlignmentSessionCreationContext,
    alignment_session_dir,
    create_alignment_session,
)
from loopora.service_types import LooporaError, LooporaWorkdirUnavailableError
from loopora.settings import load_recent_workdirs


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


def creation_context(
    repo: FakeAlignmentSessionCreationRepository,
    *,
    source_seed: dict | None = None,
    write_transcript_log: Callable[[dict], None] | None = None,
):
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
        write_transcript_log=write_transcript_log or (lambda session: logged_sessions.append(dict(session))),
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
            "event_type": "alignment_user_message",
            "payload": {"role": "user", "content": "Shape this task into a Loop."},
        },
        {
            "event_type": "alignment_source_context_selected",
            "payload": {"source_type": "bundle", "source_bundle_id": "bundle_1"},
        },
    ]
    assert logged_sessions[0]["status"] == "idle"
    assert started_sessions == ["align_fixed"]
    assert resolved_sources == [{"workdir": str(tmp_path.resolve()), "source_option_id": "bundle:bundle_1"}]
    assert load_recent_workdirs() == [str(tmp_path.resolve())]


def test_alignment_session_creation_treats_transcript_artifact_failure_as_diagnostic(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionCreationRepository()

    def fail_transcript_log(_session: dict) -> None:
        raise OSError(f"permission denied: {tmp_path / 'private' / 'transcript.jsonl'}")

    context, started_sessions, logged_sessions, _resolved_sources = creation_context(
        repo,
        write_transcript_log=fail_transcript_log,
    )

    session = create_alignment_session(
        context,
        AlignmentSessionCreateRequest(
            workdir=tmp_path,
            message="Shape this task into a Loop.",
            start_immediately=True,
        ),
    )

    assert session["status"] == "running"
    assert repo.session["transcript"] == [
        {"role": "user", "content": "Shape this task into a Loop.", "created_at": "2026-05-29T00:00:00Z"}
    ]
    assert started_sessions == ["align_fixed"]
    assert logged_sessions == []
    assert [event["event_type"] for event in repo.events] == [
        "alignment_session_created",
        "alignment_user_message",
    ]


def test_alignment_session_creation_seed_write_failure_does_not_create_half_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))
    context, started_sessions, logged_sessions, _resolved_sources = creation_context(
        repo,
        source_seed={"seed_bundle": seed_bundle},
    )
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_fixed" / "artifacts" / "bundle.yml"
    original_replace = Path.replace

    def fail_seed_replace(path: Path, target: Path) -> Path:
        if Path(target) == bundle_path and Path(path).name.startswith(f".{bundle_path.name}.tmp."):
            raise OSError(f"permission denied: {bundle_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_seed_replace)

    with pytest.raises(LooporaError, match=ALIGNMENT_SESSION_CREATE_ERROR):
        create_alignment_session(
            context,
            AlignmentSessionCreateRequest(
                workdir=tmp_path,
                message="Shape this task.",
                source_option_id="bundle:bundle_1",
                start_immediately=True,
            ),
        )

    assert repo.session == {}
    assert repo.events == []
    assert started_sessions == []
    assert logged_sessions == []
    assert not bundle_path.exists()
    assert not list(bundle_path.parent.glob(f".{bundle_path.name}.tmp.*"))


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
    assert [event["event_type"] for event in repo.events] == ["alignment_session_created"]


def test_alignment_session_creation_rejects_missing_workdir(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    context, _started_sessions, _logged_sessions, _resolved_sources = creation_context(repo)
    missing_workdir = tmp_path / "missing"

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        create_alignment_session(context, AlignmentSessionCreateRequest(workdir=missing_workdir))
    assert exc_info.value.action == "alignment"
    assert exc_info.value.workdir_state == "missing"
    assert str(exc_info.value) == f"target project is not ready for Alignment: {exc_info.value.summary}"
    assert str(missing_workdir.resolve(strict=False)) not in str(exc_info.value)
    assert load_recent_workdirs() == []


def test_alignment_session_creation_rejects_uninspectable_workdir_without_os_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = FakeAlignmentSessionCreationRepository()
    context, _started_sessions, _logged_sessions, _resolved_sources = creation_context(repo)
    blocked_workdir = tmp_path / "blocked-workdir"
    blocked_resolved = blocked_workdir.resolve(strict=False)
    private_path = tmp_path / "private" / "blocked"
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        create_alignment_session(context, AlignmentSessionCreateRequest(workdir=blocked_workdir))
    assert exc_info.value.action == "alignment"
    assert exc_info.value.workdir_state == "unavailable"
    assert "permission denied" not in str(exc_info.value)
    assert str(private_path) not in str(exc_info.value)
    assert load_recent_workdirs() == []
