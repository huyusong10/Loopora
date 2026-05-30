import json
from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_context import redact_alignment_source_value
from loopora.service_alignment_requests import (
    AlignmentExecutorSettingsRequest,
    RevisionAlignmentSessionRequest,
    default_alignment_executor_settings,
)
from loopora.service_alignment_revision import AlignmentRevisionContext, create_revision_alignment_session


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


def revision_context(repo: FakeAlignmentRevisionRepository):
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
        start_session_async=start_session_async,
        redact_source_value=redact_alignment_source_value,
        write_transcript_log=lambda session: logged_sessions.append(dict(session)),
    )
    return context, created_sessions, started_sessions, logged_sessions


def test_alignment_revision_command_writes_seed_bundle_links_source_and_starts(tmp_path: Path) -> None:
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_revision" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentRevisionRepository(
        {
            "id": "align_revision",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "working_agreement": {},
        }
    )
    context, created_sessions, started_sessions, logged_sessions = revision_context(repo)
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))
    seed_bundle["metadata"]["description"] = "Use --token REVISION_METADATA_SECRET"

    session = create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message="Improve the existing Loop.",
            start_immediately=True,
            source_context={
                "source_type": "run",
                "source_run_id": "run_1",
                "evidence_summary": [{"claim": "Authorization: Bearer REVISION_SOURCE_SECRET"}],
            },
            linked_bundle_id="bundle_1",
            linked_run_id="run_1",
            executor_settings=AlignmentExecutorSettingsRequest(
                executor_kind="custom",
                executor_mode="command",
                command_cli="loopora-runner",
                command_args_text="--resume",
                model="",
                reasoning_effort="",
            ),
        ),
    )

    assert session["status"] == "running"
    assert created_sessions == [
        {
            "workdir": tmp_path,
            "message": "Improve the existing Loop.",
            "executor_kind": "custom",
            "executor_mode": "command",
            "command_cli": "loopora-runner",
            "command_args_text": "--resume",
            "model": "",
            "reasoning_effort": "",
            "start_immediately": False,
        }
    ]
    assert bundle_path.exists()
    assert "Ship the focused starter experience" in bundle_path.read_text(encoding="utf-8")
    assert repo.session["linked_bundle_id"] == "bundle_1"
    assert repo.session["linked_run_id"] == "run_1"
    agreement_text = json.dumps(repo.session["working_agreement"], ensure_ascii=False)
    assert repo.session["working_agreement"]["mode"] == "improvement"
    assert repo.session["working_agreement"]["source"]["source_type"] == "run"
    assert "REVISION_SOURCE_SECRET" not in agreement_text
    assert "REVISION_METADATA_SECRET" not in agreement_text
    assert "<secret omitted>" in agreement_text
    assert repo.events == [
        {
            "event_type": "alignment_bundle_improvement_seeded",
            "payload": {
                "source_type": "run",
                "source_bundle_id": "bundle_1",
                "source_run_id": "run_1",
                "bundle_path": str(bundle_path),
            },
        }
    ]
    assert logged_sessions[0]["status"] == "idle"
    assert logged_sessions[0]["working_agreement"]["source"]["source_type"] == "run"
    assert started_sessions == ["align_revision"]


def test_alignment_revision_command_keeps_session_idle_when_not_starting(tmp_path: Path) -> None:
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_revision" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentRevisionRepository(
        {
            "id": "align_revision",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "working_agreement": {},
        }
    )
    context, _created_sessions, started_sessions, logged_sessions = revision_context(repo)
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))

    session = create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message="Improve later.",
            start_immediately=False,
            source_context={"source_type": "bundle", "source_bundle_id": "bundle_2"},
            linked_bundle_id="bundle_2",
            linked_run_id="",
            executor_settings=default_alignment_executor_settings(),
        ),
    )

    assert session["status"] == "idle"
    assert started_sessions == []
    assert logged_sessions[0]["linked_bundle_id"] == "bundle_2"
