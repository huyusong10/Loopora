import json
from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_requests import AlignmentExecutorSettingsRequest, RevisionAlignmentSessionRequest
import pytest

from loopora.service_alignment_revision import REVISION_SESSION_CREATE_ERROR, create_revision_alignment_session
from loopora.service_types import LooporaError

from alignment_revision_test_support import FakeAlignmentRevisionRepository, revision_context


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


def test_alignment_revision_treats_transcript_artifact_failure_as_diagnostic(tmp_path: Path) -> None:
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_revision" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentRevisionRepository(
        {
            "id": "align_revision",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "working_agreement": {},
        }
    )

    def fail_transcript_log(_session: dict) -> None:
        raise OSError(f"permission denied: {tmp_path / 'private' / 'transcript.jsonl'}")

    context, _created_sessions, started_sessions, logged_sessions = revision_context(
        repo,
        write_transcript_log=fail_transcript_log,
    )
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))

    session = create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message="Improve the existing Loop.",
            start_immediately=True,
            source_context={"source_type": "bundle", "source_bundle_id": "bundle_1"},
            linked_bundle_id="bundle_1",
            linked_run_id="",
            executor_settings=AlignmentExecutorSettingsRequest(
                executor_kind="codex",
                executor_mode="preset",
                command_cli="",
                command_args_text="",
                model="",
                reasoning_effort="",
            ),
        ),
    )

    assert session["status"] == "running"
    assert repo.session["linked_bundle_id"] == "bundle_1"
    assert repo.session["working_agreement"]["mode"] == "improvement"
    assert repo.events == [
        {
            "event_type": "alignment_bundle_improvement_seeded",
            "payload": {
                "source_type": "bundle",
                "source_bundle_id": "bundle_1",
                "source_run_id": "",
                "bundle_path": str(bundle_path),
            },
        }
    ]
    assert started_sessions == ["align_revision"]
    assert logged_sessions == []


def test_alignment_revision_seed_write_failure_marks_session_failed_without_start(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
    original_replace = Path.replace

    def fail_seed_replace(path: Path, target: Path) -> Path:
        if Path(target) == bundle_path and Path(path).name.startswith(f".{bundle_path.name}.tmp."):
            raise OSError(f"permission denied: {bundle_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_seed_replace)

    with pytest.raises(LooporaError, match=REVISION_SESSION_CREATE_ERROR):
        create_revision_alignment_session(
            context,
            RevisionAlignmentSessionRequest(
                seed_bundle=seed_bundle,
                message="Improve the existing Loop.",
                start_immediately=True,
                source_context={"source_type": "bundle", "source_bundle_id": "bundle_1"},
                linked_bundle_id="bundle_1",
                linked_run_id="",
                executor_settings=AlignmentExecutorSettingsRequest(
                    executor_kind="codex",
                    executor_mode="preset",
                    command_cli="",
                    command_args_text="",
                    model="",
                    reasoning_effort="",
                ),
            ),
        )

    assert created_sessions == [
        {
            "workdir": tmp_path,
            "message": "Improve the existing Loop.",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
            "start_immediately": False,
        }
    ]
    assert repo.session["status"] == "failed"
    assert repo.session["error_message"] == REVISION_SESSION_CREATE_ERROR
    assert repo.events == [
        {
            "event_type": "alignment_bundle_improvement_seed_failed",
            "payload": {"status": "failed", "error": REVISION_SESSION_CREATE_ERROR},
        }
    ]
    assert started_sessions == []
    assert logged_sessions == []
    assert not bundle_path.exists()
    assert not list(bundle_path.parent.glob(f".{bundle_path.name}.tmp.*"))
