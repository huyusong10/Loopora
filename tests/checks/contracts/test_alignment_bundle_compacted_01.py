from __future__ import annotations

# Merged from test_alignment_bundle_import_run_payloads.py
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_alignment_bundle_lifecycle import (
    alignment_import_failed_event_payload,
    alignment_imported_event_payload,
    alignment_imported_update_fields,
    alignment_run_start_failed_event_payload,
    alignment_run_started_event_payload,
)


def test_alignment_bundle_import_and_run_event_payloads() -> None:
    validation = {"ok": True}
    bundle = {"id": "bundle_1", "loop_id": "loop_1"}
    run = {"id": "run_1"}

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
    assert alignment_run_start_failed_event_payload(bundle, "boom") == {
        "bundle_id": "bundle_1",
        "loop_id": "loop_1",
        "error": "boom",
    }
    assert alignment_run_start_failed_event_payload(bundle, BACKGROUND_WORKER_START_ERROR, run) == {
        "bundle_id": "bundle_1",
        "loop_id": "loop_1",
        "error": BACKGROUND_WORKER_START_ERROR,
        "run_id": "run_1",
        "run_start_error": BACKGROUND_WORKER_START_ERROR,
        "run_recovery": "retry_run_start",
        "next_action_kinds": ["retry_web_run_start"],
        "next_action_ready_kinds": ["retry_web_run_start"],
        "next_action_ready_now_kinds": ["retry_web_run_start"],
        "next_action_ready_after_actions": {},
        "next_action_blocked_kinds": [],
        "next_action_command_blockers": {},
        "next_actions": [
            {
                "kind": "retry_web_run_start",
                "target": "web_loop_start",
                "action": "start_run",
                "loop_id": "loop_1",
            }
        ],
    }
    assert alignment_run_started_event_payload(bundle, run) == {
        "bundle_id": "bundle_1",
        "loop_id": "loop_1",
        "run_id": "run_1",
    }


# Merged from test_alignment_bundle_lifecycle_events.py
from pathlib import Path

from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    apply_alignment_bundle_sync_failure,
    apply_alignment_bundle_sync_success,
    apply_alignment_bundle_write_started,
    apply_alignment_imported,
    apply_alignment_run_started,
    apply_alignment_validation_success,
)

from compacted_contract_support import FakeAlignmentLifecycleRepository, lifecycle_context


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
    context = lifecycle_context(repo, validation_logs)

    started = apply_alignment_bundle_write_started(
        repo,
        "align_1",
        bundle_path=bundle_path,
        bundle_yaml="version: 1\n",
    )
    apply_alignment_validation_success(context, "align_1", validation=validation)
    synced = apply_alignment_bundle_sync_success(context, "align_1", validation=validation)
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


def test_alignment_bundle_lifecycle_treats_validation_artifact_failure_as_diagnostic(tmp_path: Path) -> None:
    bundle_path = tmp_path / "align_1" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentLifecycleRepository(
        {
            "id": "align_1",
            "status": "ready",
            "bundle_path": str(bundle_path),
            "transcript": [],
        }
    )

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def fail_validation_log(_session: dict, _validation: dict) -> None:
        raise OSError(f"permission denied: {tmp_path / 'private' / 'validation.json'}")

    context = AlignmentBundleLifecycleContext(
        repository=repo,
        get_session=get_session,
        write_validation_log=fail_validation_log,
    )

    synced = apply_alignment_bundle_sync_success(
        context,
        "align_1",
        validation={"ok": True, "semantic_lint": {"ok": True, "issues": []}},
    )
    failed = apply_alignment_bundle_sync_failure(
        context,
        "align_1",
        validation={"ok": False, "error": "bad bundle"},
        finished_at="later",
    )

    assert synced["status"] == "ready"
    assert failed["ok"] is False
    assert repo.session["status"] == "failed"
    assert [event["event_type"] for event in repo.events] == [
        "alignment_bundle_synced",
        "alignment_bundle_sync_failed",
    ]


# Merged from test_alignment_bundle_preview_draft_paths.py

from alignment_bundle_preview_test_support import (
    bundle_session,
    preview_alignment_bundle,
    write_alignment_bundle,
)


def test_alignment_bundle_preview_reports_missing_bundle_without_building_preview(tmp_path: Path) -> None:
    session = bundle_session(
        "align_missing",
        "ready",
        tmp_path / "missing.yml",
        validation={"ok": False, "error": "previous validation error"},
    )

    result = preview_alignment_bundle(session)

    assert result == {
        "ok": False,
        "session": session,
        "yaml": "",
        "bundle": None,
        "validation": {
            "ok": False,
            "error": "alignment bundle does not exist",
            "bundle_path": str(tmp_path / "missing.yml"),
            "checked_at": "2026-05-29T00:00:00Z",
            "semantic_lint": {"ok": False, "issues": ["alignment bundle does not exist"]},
        },
    }


def test_alignment_bundle_preview_normalizes_draft_bundle_without_ready_validation(tmp_path: Path) -> None:
    bundle_path, _raw_yaml = write_alignment_bundle(tmp_path)
    session = bundle_session("align_idle", "idle", bundle_path)

    result = preview_alignment_bundle(session)

    assert result["ok"] is True
    assert result["session"] is session
    assert result["source_path"] == str(bundle_path)
    assert result["bundle"]["loop"]["workdir"] == str(tmp_path)
    assert result["validation"] == {"ok": True, "bundle_path": str(bundle_path)}
    assert result["yaml"].startswith("version: 1\n")


def test_alignment_bundle_preview_returns_failure_validation_with_raw_yaml(tmp_path: Path) -> None:
    raw_yaml = "version: 1\nmetadata:\n  name: [\n"
    bundle_path, _raw_yaml = write_alignment_bundle(tmp_path, raw_yaml=raw_yaml)
    session = bundle_session("align_invalid", "idle", bundle_path)

    result = preview_alignment_bundle(session, now="2026-05-29T00:02:00Z")

    assert result["ok"] is False
    assert result["bundle"] is None
    assert result["yaml"] == raw_yaml
    assert result["validation"]["ok"] is False
    assert result["validation"]["checked_at"] == "2026-05-29T00:02:00Z"


# Merged from test_alignment_bundle_preview_ready_validation.py

from loopora.bundles import load_bundle_text
from loopora.service_types import LooporaError


def test_alignment_bundle_preview_revalidates_ready_statuses(tmp_path: Path) -> None:
    bundle_path, raw_yaml = write_alignment_bundle(tmp_path)
    session = bundle_session("align_ready", "ready", bundle_path)

    def load_validated(session_arg: dict, raw_yaml_arg: str, semantic_issues: list[str]) -> tuple[dict, str]:
        assert session_arg is session
        assert raw_yaml_arg == raw_yaml
        assert semantic_issues == []
        return load_bundle_text(raw_yaml_arg), "version: 1\nmetadata:\n  name: Normalized\n"

    result = preview_alignment_bundle(
        session,
        load_validated_bundle_text=load_validated,
        now="2026-05-29T00:01:00Z",
    )

    assert result["ok"] is True
    assert result["validation"]["ok"] is True
    assert result["validation"]["checked_at"] == "2026-05-29T00:01:00Z"
    assert result["validation"]["semantic_lint"] == {"ok": True, "issues": []}
    assert result["yaml"] == "version: 1\nmetadata:\n  name: Normalized\n"


def test_alignment_bundle_preview_preserves_semantic_issues_from_ready_validation(tmp_path: Path) -> None:
    bundle_path, _raw_yaml = write_alignment_bundle(tmp_path)
    session = bundle_session("align_ready_invalid", "imported", bundle_path)

    def fail_validated(_session: dict, _raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        semantic_issues.append("spec.markdown")
        raise LooporaError("semantic lint failed")

    result = preview_alignment_bundle(
        session,
        load_validated_bundle_text=fail_validated,
        now="2026-05-29T00:03:00Z",
    )

    assert result["ok"] is False
    assert result["validation"]["semantic_lint"] == {"ok": False, "issues": ["spec.markdown"]}


# Merged from test_alignment_bundle_stage_error.py
from loopora.service_alignment_stage import AlignmentBundleStageGate, alignment_bundle_stage_error


def test_alignment_bundle_stage_error_prioritizes_stage_and_readiness_gates() -> None:
    kwargs = {
        "confirmed_stages": {"confirmed"},
        "phase": "bundle",
        "agreement_summary": "Agreement",
        "checklist": {"loop_fit": True},
        "readiness_keys": ["loop_fit"],
        "evidence_issues": [],
        "improvement_issues": [],
        "language_issues": [],
        "prefers_chinese": False,
    }

    assert "explicit confirmation" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="clarifying", **kwargs))
    assert "finish alignment before generating" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "phase": "agreement"}))
    assert "confirmed working agreement summary" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "agreement_summary": ""})
    )
    assert "readiness checklist" in alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "checklist": []}))
    assert "readiness checks are incomplete: Loopora fit" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(stage="confirmed", **{**kwargs, "checklist": {"loop_fit": False}}),
    )
    assert alignment_bundle_stage_error(AlignmentBundleStageGate(stage="confirmed", **kwargs)) == ""


def test_alignment_bundle_stage_error_reports_evidence_improvement_and_language_gates() -> None:
    kwargs = {
        "stage": "confirmed",
        "confirmed_stages": {"confirmed"},
        "phase": "bundle",
        "agreement_summary": "Agreement",
        "checklist": {"loop_fit": True},
        "readiness_keys": ["loop_fit"],
        "prefers_chinese": True,
    }

    assert "对齐证据" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=["readiness_evidence"], improvement_issues=[], language_issues=[]),
    )
    assert "改进变化" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=[], improvement_issues=["improvement_delta"], language_issues=[]),
    )
    assert "需要使用中文：工作协议摘要" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(**kwargs, evidence_issues=[], improvement_issues=[], language_issues=["agreement_summary"]),
    )
    assert "need the user's language: agreement summary" in alignment_bundle_stage_error(
        AlignmentBundleStageGate(
            **{**kwargs, "prefers_chinese": False},
            evidence_issues=[],
            improvement_issues=[],
            language_issues=["agreement_summary"],
        ),
    )


# Merged from test_alignment_bundle_stage_progression.py

from alignment_test_support import _assert_alignment_stage_blocked, _wait_for_status


def test_alignment_service_blocks_premature_bundle_output(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_premature_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "finish alignment" in session["transcript"][-1]["content"]
    assert "Loop plan" in session["transcript"][-1]["content"]
    _assert_alignment_stage_blocked(service, created["id"])


# Merged from test_alignment_bundle_sync_payloads.py

from loopora.service_alignment_bundle_lifecycle import (
    alignment_bundle_missing_file_validation,
    alignment_bundle_sync_failure_result,
    alignment_bundle_sync_failure_update_fields,
    alignment_bundle_sync_success_update_fields,
)


def test_alignment_bundle_sync_payloads_keep_status_and_result_shape(tmp_path: Path) -> None:
    bundle_path = tmp_path / "missing.yml"
    validation = alignment_bundle_missing_file_validation(bundle_path, checked_at="now")
    update_fields = alignment_bundle_sync_failure_update_fields(validation, finished_at="later")
    result = alignment_bundle_sync_failure_result({"id": "align_1"}, validation)

    assert validation["semantic_lint"]["issues"] == ["alignment bundle does not exist"]
    assert update_fields == {
        "status": "failed",
        "validation": validation,
        "error_message": validation["error"],
        "finished_at": "later",
        "clear_active_child_pid": True,
    }
    assert result == {"ok": False, "session": {"id": "align_1"}, "yaml": "", "bundle": None, "validation": validation}


def test_alignment_bundle_sync_success_updates_ready_stage() -> None:
    validation = {"ok": True}

    assert alignment_bundle_sync_success_update_fields(validation) == {
        "status": "ready",
        "alignment_stage": "ready",
        "validation": validation,
        "error_message": "",
        "finished_at": None,
    }


# Merged from test_alignment_bundle_validation_payloads.py
from hashlib import sha256

from loopora.service_alignment_bundle_lifecycle import (
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
)


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


# Merged from test_alignment_bundle_written_payload.py

from loopora.service_alignment_bundle_lifecycle import alignment_bundle_written_event_payload


def test_alignment_bundle_written_event_payload_hashes_raw_bundle_text(tmp_path: Path) -> None:
    bundle_yaml = "version: 1\n"
    payload = alignment_bundle_written_event_payload(tmp_path / "bundle.yml", bundle_yaml)

    assert payload["size"] == len(bundle_yaml)
    assert payload["bundle_sha256"] == sha256(bundle_yaml.encode("utf-8")).hexdigest()
