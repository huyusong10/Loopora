from pathlib import Path

import pytest

from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_bundle_validation_payloads import ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
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

    def append_notice_message(session_id: str, content: str) -> dict:
        assert session_id == repo.session["id"]
        transcript = list(repo.session.get("transcript") or [])
        transcript.append({"role": "assistant", "content": content, "created_at": "2026-05-30T00:00:00Z"})
        repo.session["transcript"] = transcript
        repo.append_alignment_event(session_id, "alignment_message", {"role": "assistant", "content": content})
        return dict(repo.session)

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=lambda session, validation: validation_logs.append({"session": session, "validation": validation}),
        )

    def build_preview(bundle: dict, *, source_path: str, validation: dict) -> dict:
        preview_requests.append({"bundle": bundle, "source_path": source_path, "validation": validation})
        return {"ok": True, "bundle": bundle, "validation": validation}

    context = AlignmentSyncContext(
        get_session=get_session,
        load_validated_bundle_text=load_validated_bundle_text,
        append_notice_message=append_notice_message,
        bundle_lifecycle_context=lifecycle_context,
        build_preview=build_preview,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, validation_logs, preview_requests


def ready_session(tmp_path: Path, *, status: str = "ready") -> dict:
    bundle_path = tmp_path / "align_sync" / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {"id": "align_sync", "status": status, "bundle_path": str(bundle_path), "transcript": [], "working_agreement": {}}


def test_alignment_sync_command_reloads_normalizes_logs_and_returns_preview(tmp_path: Path) -> None:
    repo, context, validation_logs, preview_requests = sync_case(tmp_path)

    result = sync_bundle(context, active_statuses=("running", "validating", "repairing"))

    bundle_path = Path(repo.session["bundle_path"])
    assert result["ok"] is True
    assert result["session"]["status"] == "ready"
    assert result["yaml"] == "version: 1\n# normalized\n"
    assert bundle_path.read_text(encoding="utf-8") == "version: 1\n# normalized\n"
    assert repo.session["error_message"] == ""
    assert repo.session["finished_at"] is None
    assert repo.session["transcript"][-1]["content"] == "Reloaded bundle.yml and validation passed."
    assert preview_requests == [{"bundle": {"loop": {"name": "Synced Loop"}}, "source_path": str(bundle_path), "validation": result["validation"]}]
    assert validation_logs[0]["validation"]["ok"] is True
    assert_event_types(repo, "alignment_message", "alignment_bundle_synced")


def test_alignment_sync_command_records_missing_file_failure(tmp_path: Path) -> None:
    repo, context, validation_logs, _preview_requests = sync_case(tmp_path)
    Path(repo.session["bundle_path"]).unlink()

    result = sync_bundle(context)

    assert result["ok"] is False
    assert result["bundle"] is None
    assert repo.session["status"] == "failed"
    assert repo.session["validation"]["ok"] is False
    assert repo.session["error_message"] == "alignment bundle does not exist"
    assert repo.session["validation"]["semantic_lint"]["issues"] == ["alignment bundle does not exist"]
    assert str(tmp_path) not in repo.session["error_message"]
    assert str(tmp_path) not in repo.session["validation"]["error"]
    assert str(tmp_path) not in repo.session["validation"]["semantic_lint"]["issues"][0]
    assert repo.session["transcript"][-1]["content"].startswith("Failed to reload bundle.yml:")
    assert validation_logs[0]["validation"]["semantic_lint"]["ok"] is False
    assert_event_types(repo, "alignment_message", "alignment_bundle_sync_failed")


@pytest.mark.parametrize(("status", "message"), [("running", "cannot sync bundle while alignment session is active"), ("imported", "cannot sync bundle in status imported")])
def test_alignment_sync_command_rejects_invalid_statuses(tmp_path: Path, status: str, message: str) -> None:
    _repo, context, _validation_logs, _preview_requests = sync_case(tmp_path, status=status)
    with pytest.raises(LooporaConflictError, match=message):
        sync_bundle(context)


def test_alignment_sync_command_records_validation_failure(tmp_path: Path) -> None:
    repo, context, validation_logs, _preview_requests = sync_case(
        tmp_path,
        validation_error=LooporaError("bundle semantic lint failed"),
    )

    result = sync_bundle(context)

    assert result["ok"] is False
    assert repo.session["status"] == "failed"
    assert repo.session["error_message"] == "bundle semantic lint failed"
    assert validation_logs[0]["validation"]["semantic_lint"] == {"ok": False, "issues": ["semantic gap"]}
    assert_event_types(repo, "alignment_message", "alignment_bundle_sync_failed")


def test_alignment_sync_command_records_save_failure_without_local_details(tmp_path: Path, monkeypatch) -> None:
    repo, context, validation_logs, _preview_requests = sync_case(tmp_path)
    bundle_path = Path(repo.session["bundle_path"])
    original_yaml = bundle_path.read_text(encoding="utf-8")
    original_replace = Path.replace

    def fail_bundle_save_only(path: Path, target: Path):
        if Path(target) == bundle_path and Path(path).name.startswith(f".{bundle_path.name}.tmp."):
            raise OSError(f"permission denied: {bundle_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_save_only)

    result = sync_bundle(context)

    assert result["ok"] is False
    assert repo.session["status"] == "failed"
    assert repo.session["error_message"] == ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
    assert repo.session["validation"]["error"] == ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
    assert repo.session["validation"]["semantic_lint"]["issues"] == [ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR]
    assert validation_logs[0]["validation"]["error"] == ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
    encoded_session = str(repo.session)
    assert "permission denied" not in encoded_session
    assert str(bundle_path) not in repo.session["error_message"]
    assert str(bundle_path) not in repo.session["validation"]["error"]
    assert str(bundle_path) not in repo.session["transcript"][-1]["content"]
    assert bundle_path.read_text(encoding="utf-8") == original_yaml
    assert not list(bundle_path.parent.glob(f".{bundle_path.name}.tmp.*"))
    assert_event_types(repo, "alignment_message", "alignment_bundle_sync_failed")


def sync_case(tmp_path: Path, *, status: str = "ready", validation_error: Exception | None = None):
    repo = FakeAlignmentSyncRepository(ready_session(tmp_path, status=status))
    context, validation_logs, preview_requests = sync_context(repo, validation_error=validation_error)
    return repo, context, validation_logs, preview_requests


def assert_event_types(repo: FakeAlignmentSyncRepository, *event_types: str) -> None:
    assert [event["event_type"] for event in repo.events] == list(event_types)


def sync_bundle(context: AlignmentSyncContext, *, active_statuses: tuple[str, ...] = ("running",)) -> dict:
    return sync_alignment_bundle_from_file(context, "align_sync", active_statuses=set(active_statuses))
