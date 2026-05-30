from pathlib import Path

import pytest

from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_sync import AlignmentSyncContext, sync_alignment_bundle_from_file
from loopora.service_types import LooporaConflictError, LooporaError


class FakeAlignmentSyncRepository:
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


def sync_context(repo: FakeAlignmentSyncRepository, *, validation_error: Exception | None = None):
    validation_logs: list[dict] = []
    preview_requests: list[dict] = []

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def load_validated_bundle_text(_session: dict, raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        if validation_error is not None:
            semantic_issues.append("semantic gap")
            raise validation_error
        return {"loop": {"name": "Synced Loop"}}, raw_yaml.rstrip() + "\n# normalized\n"

    def append_system_message(session_id: str, zh: str, _en: str) -> dict:
        assert session_id == repo.session["id"]
        transcript = list(repo.session.get("transcript") or [])
        transcript.append({"role": "assistant", "content": zh, "created_at": "2026-05-30T00:00:00Z"})
        repo.session["transcript"] = transcript
        repo.append_alignment_event(session_id, "alignment_message", {"role": "assistant", "content": zh})
        return dict(repo.session)

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=lambda session, validation: validation_logs.append(
                {"session": session, "validation": validation}
            ),
        )

    def build_preview(bundle: dict, *, source_path: str, validation: dict) -> dict:
        preview_requests.append({"bundle": bundle, "source_path": source_path, "validation": validation})
        return {"ok": True, "bundle": bundle, "validation": validation}

    context = AlignmentSyncContext(
        get_session=get_session,
        load_validated_bundle_text=load_validated_bundle_text,
        append_system_message=append_system_message,
        bundle_lifecycle_context=lifecycle_context,
        build_preview=build_preview,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, validation_logs, preview_requests


def ready_session(tmp_path: Path, *, status: str = "ready") -> dict:
    bundle_path = tmp_path / "align_sync" / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {
        "id": "align_sync",
        "status": status,
        "bundle_path": str(bundle_path),
        "transcript": [],
        "working_agreement": {},
    }


def test_alignment_sync_command_reloads_normalizes_logs_and_returns_preview(tmp_path: Path) -> None:
    repo = FakeAlignmentSyncRepository(ready_session(tmp_path))
    context, validation_logs, preview_requests = sync_context(repo)

    result = sync_alignment_bundle_from_file(
        context,
        "align_sync",
        active_statuses={"running", "validating", "repairing"},
    )

    bundle_path = Path(repo.session["bundle_path"])
    assert result["ok"] is True
    assert result["session"]["status"] == "ready"
    assert result["yaml"] == "version: 1\n# normalized\n"
    assert bundle_path.read_text(encoding="utf-8") == "version: 1\n# normalized\n"
    assert repo.session["error_message"] == ""
    assert repo.session["finished_at"] is None
    assert repo.session["transcript"][-1]["content"] == "已重新读取 bundle.yml，并校验通过。"
    assert preview_requests == [
        {
            "bundle": {"loop": {"name": "Synced Loop"}},
            "source_path": str(bundle_path),
            "validation": result["validation"],
        }
    ]
    assert validation_logs[0]["validation"]["ok"] is True
    assert [event["event_type"] for event in repo.events] == ["alignment_message", "alignment_bundle_synced"]


def test_alignment_sync_command_records_missing_file_failure(tmp_path: Path) -> None:
    session = ready_session(tmp_path)
    Path(session["bundle_path"]).unlink()
    repo = FakeAlignmentSyncRepository(session)
    context, validation_logs, _preview_requests = sync_context(repo)

    result = sync_alignment_bundle_from_file(context, "align_sync", active_statuses={"running"})

    assert result["ok"] is False
    assert result["bundle"] is None
    assert repo.session["status"] == "failed"
    assert repo.session["validation"]["ok"] is False
    assert "alignment bundle does not exist" in repo.session["error_message"]
    assert repo.session["transcript"][-1]["content"].startswith("重新读取 bundle.yml 失败：")
    assert validation_logs[0]["validation"]["semantic_lint"]["ok"] is False
    assert [event["event_type"] for event in repo.events] == ["alignment_message", "alignment_bundle_sync_failed"]


def test_alignment_sync_command_rejects_invalid_statuses(tmp_path: Path) -> None:
    active_repo = FakeAlignmentSyncRepository(ready_session(tmp_path, status="running"))
    active_context, _validation_logs, _preview_requests = sync_context(active_repo)
    with pytest.raises(LooporaConflictError, match="cannot sync bundle while alignment session is active"):
        sync_alignment_bundle_from_file(active_context, "align_sync", active_statuses={"running"})

    imported_repo = FakeAlignmentSyncRepository(ready_session(tmp_path, status="imported"))
    imported_context, _validation_logs, _preview_requests = sync_context(imported_repo)
    with pytest.raises(LooporaConflictError, match="cannot sync bundle in status imported"):
        sync_alignment_bundle_from_file(imported_context, "align_sync", active_statuses={"running"})


def test_alignment_sync_command_records_validation_failure(tmp_path: Path) -> None:
    repo = FakeAlignmentSyncRepository(ready_session(tmp_path))
    context, validation_logs, _preview_requests = sync_context(repo, validation_error=LooporaError("bundle semantic lint failed"))

    result = sync_alignment_bundle_from_file(context, "align_sync", active_statuses={"running"})

    assert result["ok"] is False
    assert repo.session["status"] == "failed"
    assert repo.session["error_message"] == "bundle semantic lint failed"
    assert validation_logs[0]["validation"]["semantic_lint"] == {"ok": False, "issues": ["semantic gap"]}
    assert [event["event_type"] for event in repo.events] == ["alignment_message", "alignment_bundle_sync_failed"]
