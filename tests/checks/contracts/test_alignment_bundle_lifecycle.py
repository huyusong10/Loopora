from hashlib import sha256
from pathlib import Path

from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    apply_alignment_bundle_sync_failure,
    apply_alignment_bundle_sync_success,
    apply_alignment_bundle_write_started,
    apply_alignment_imported,
    apply_alignment_run_started,
    apply_alignment_validation_success,
    alignment_bundle_missing_file_validation,
    alignment_bundle_sync_failure_result,
    alignment_bundle_sync_failure_update_fields,
    alignment_bundle_sync_success_update_fields,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
    alignment_bundle_written_event_payload,
    alignment_import_failed_event_payload,
    alignment_imported_event_payload,
    alignment_imported_update_fields,
    alignment_run_start_failed_event_payload,
    alignment_run_started_event_payload,
)


class FakeAlignmentLifecycleRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def test_alignment_bundle_validation_payloads_preserve_semantic_lint(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    success = alignment_bundle_validation_success(
        bundle_path,
        checked_at="2026-05-29T00:00:00Z",
        normalized_yaml="version: 1\n",
    )
    failure = alignment_bundle_validation_failure(
        bundle_path,
        error="bad bundle",
        semantic_issues=["spec.markdown"],
        checked_at="2026-05-29T00:00:01Z",
    )

    assert success["ok"] is True
    assert success["bundle_sha256"] == sha256(b"version: 1\n").hexdigest()
    assert success["semantic_lint"] == {"ok": True, "issues": []}
    assert failure["ok"] is False
    assert failure["semantic_lint"] == {"ok": False, "issues": ["spec.markdown"]}


def test_alignment_bundle_sync_payloads_keep_status_and_result_shape(tmp_path: Path) -> None:
    bundle_path = tmp_path / "missing.yml"
    validation = alignment_bundle_missing_file_validation(bundle_path, checked_at="now")
    update_fields = alignment_bundle_sync_failure_update_fields(validation, finished_at="later")
    result = alignment_bundle_sync_failure_result({"id": "align_1"}, validation)

    assert validation["semantic_lint"]["issues"] == [f"alignment bundle does not exist: {bundle_path}"]
    assert update_fields == {
        "status": "failed",
        "validation": validation,
        "error_message": validation["error"],
        "finished_at": "later",
        "clear_active_child_pid": True,
    }
    assert result == {"ok": False, "session": {"id": "align_1"}, "yaml": "", "bundle": None, "validation": validation}


def test_alignment_bundle_import_and_run_event_payloads() -> None:
    validation = {"ok": True}
    bundle = {"id": "bundle_1", "loop_id": "loop_1"}
    run = {"id": "run_1"}

    assert alignment_bundle_sync_success_update_fields(validation) == {
        "status": "ready",
        "alignment_stage": "ready",
        "validation": validation,
        "error_message": "",
        "finished_at": None,
    }
    assert alignment_imported_update_fields(bundle, validation) == {
        "status": "imported",
        "linked_bundle_id": "bundle_1",
        "linked_loop_id": "loop_1",
        "linked_run_id": "",
        "validation": validation,
        "error_message": "",
    }
    assert alignment_import_failed_event_payload("bad", {"semantic_lint": {"ok": False}}) == {
        "error": "bad",
        "status": "ready",
        "semantic_lint": {"ok": False},
    }
    assert alignment_imported_event_payload(bundle) == {"bundle_id": "bundle_1", "loop_id": "loop_1"}
    assert alignment_run_start_failed_event_payload(bundle, "boom") == {"bundle_id": "bundle_1", "loop_id": "loop_1", "error": "boom"}
    assert alignment_run_started_event_payload(bundle, run) == {"bundle_id": "bundle_1", "loop_id": "loop_1", "run_id": "run_1"}


def test_alignment_bundle_written_event_payload_hashes_raw_bundle_text(tmp_path: Path) -> None:
    bundle_yaml = "version: 1\n"
    payload = alignment_bundle_written_event_payload(tmp_path / "bundle.yml", bundle_yaml)

    assert payload["size"] == len(bundle_yaml)
    assert payload["bundle_sha256"] == sha256(bundle_yaml.encode("utf-8")).hexdigest()


def test_alignment_bundle_lifecycle_applies_repository_events_and_logs(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_1" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentLifecycleRepository(
        {
            "id": "align_1",
            "status": "ready",
            "bundle_path": str(bundle_path),
            "transcript": [],
        }
    )
    validation = {"ok": True, "semantic_lint": {"ok": True, "issues": []}}
    validation_logs: list[tuple[str, dict]] = []

    def get_session(session_id: str) -> dict:
        assert session_id == "align_1"
        return dict(repo.session)

    def write_validation_log(session: dict, payload: dict) -> None:
        validation_logs.append((session["id"], payload))

    context = AlignmentBundleLifecycleContext(
        repository=repo,
        get_session=get_session,
        write_validation_log=write_validation_log,
    )
    started = apply_alignment_bundle_write_started(
        repo,
        "align_1",
        bundle_path=bundle_path,
        bundle_yaml="version: 1\n",
    )
    apply_alignment_validation_success(
        context,
        "align_1",
        validation=validation,
    )
    synced = apply_alignment_bundle_sync_success(
        context,
        "align_1",
        validation=validation,
    )
    apply_alignment_imported(
        context,
        "align_1",
        bundle={"id": "bundle_1", "loop_id": "loop_1"},
        validation=validation,
    )
    apply_alignment_run_started(
        repo,
        "align_1",
        bundle={"id": "bundle_1", "loop_id": "loop_1"},
        run={"id": "run_1"},
    )
    failed = apply_alignment_bundle_sync_failure(
        context,
        "align_1",
        validation={"ok": False, "error": "bad bundle"},
        finished_at="later",
    )

    assert started["status"] == "validating"
    assert synced["status"] == "ready"
    assert repo.session["status"] == "failed"
    assert repo.session["linked_bundle_id"] == "bundle_1"
    assert repo.session["linked_run_id"] == "run_1"
    assert failed["ok"] is False
    assert [event["event_type"] for event in repo.events] == [
        "alignment_bundle_written",
        "alignment_validation_passed",
        "alignment_bundle_synced",
        "alignment_imported",
        "alignment_run_started",
        "alignment_bundle_sync_failed",
    ]
    assert [item[0] for item in validation_logs] == ["align_1", "align_1", "align_1", "align_1"]
