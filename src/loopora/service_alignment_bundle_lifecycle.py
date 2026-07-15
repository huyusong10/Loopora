from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from loopora.service_alignment_artifacts import write_alignment_transcript_log
from loopora.service_alignment_bundle_preview import (
    alignment_bundle_missing_file_validation as alignment_bundle_missing_file_validation,
    alignment_bundle_validation_failure as alignment_bundle_validation_failure,
    alignment_bundle_validation_success as alignment_bundle_validation_success,
)


class AlignmentBundleLifecycleRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


AlignmentSessionGetter = Callable[[str], dict]
AlignmentValidationLogWriter = Callable[[dict, dict], None]


@dataclass(frozen=True)
class AlignmentBundleLifecycleContext:
    repository: AlignmentBundleLifecycleRepository
    get_session: AlignmentSessionGetter
    write_validation_log: AlignmentValidationLogWriter


def alignment_bundle_written_event_payload(bundle_path: Path, bundle_yaml: str) -> dict:
    return {
        "bundle_path": str(bundle_path),
        "size": len(bundle_yaml),
        "bundle_sha256": sha256(bundle_yaml.encode("utf-8")).hexdigest(),
    }


def alignment_bundle_sync_success_update_fields(validation: dict) -> dict:
    return {
        "status": "ready",
        "alignment_stage": "ready",
        "validation": validation,
        "error_message": "",
        "finished_at": None,
    }


def alignment_bundle_sync_failure_update_fields(validation: dict, *, finished_at: str) -> dict:
    error = str(validation.get("error", "") or "bundle validation failed")
    return {
        "status": "failed",
        "validation": validation,
        "error_message": error,
        "finished_at": finished_at,
        "clear_active_child_pid": True,
    }


def alignment_bundle_sync_failure_result(session: dict, validation: dict) -> dict:
    return {
        "ok": False,
        "session": session,
        "yaml": "",
        "bundle": None,
        "validation": validation,
    }


def alignment_import_failed_event_payload(error: str, validation: dict) -> dict:
    return {"error": error, "status": "ready", "semantic_lint": validation["semantic_lint"]}


def alignment_imported_update_fields(bundle: dict, validation: dict) -> dict:
    return {
        "status": "imported",
        "linked_bundle_id": bundle["id"],
        "linked_loop_id": bundle.get("loop_id", ""),
        "linked_run_id": "",
        "validation": validation,
        "error_message": "",
    }


def alignment_imported_event_payload(bundle: dict) -> dict:
    return {"bundle_id": bundle["id"], "loop_id": bundle.get("loop_id", "")}


def alignment_run_start_failed_event_payload(bundle: dict, error: str) -> dict:
    return {"bundle_id": bundle["id"], "loop_id": bundle.get("loop_id", ""), "error": error}


def alignment_run_started_event_payload(bundle: dict, run: dict) -> dict:
    return {"bundle_id": bundle["id"], "loop_id": bundle.get("loop_id", ""), "run_id": run["id"]}


def apply_alignment_bundle_write_started(
    repository: AlignmentBundleLifecycleRepository,
    session_id: str,
    *,
    bundle_path: Path,
    bundle_yaml: str,
) -> dict:
    session = repository.update_alignment_session(session_id, status="validating", alignment_stage="compiling")
    repository.append_alignment_event(
        session_id,
        "alignment_bundle_written",
        alignment_bundle_written_event_payload(bundle_path, bundle_yaml),
    )
    return session


def apply_alignment_validation_failure(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    validation: dict,
    error: str,
) -> None:
    repository = context.repository
    repository.update_alignment_session(session_id, validation=validation, error_message=error)
    context.write_validation_log(context.get_session(session_id), validation)
    repository.append_alignment_event(session_id, "alignment_validation_failed", validation)


def apply_alignment_validation_success(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    validation: dict,
) -> None:
    repository = context.repository
    repository.update_alignment_session(session_id, validation=validation)
    context.write_validation_log(context.get_session(session_id), validation)
    repository.append_alignment_event(session_id, "alignment_validation_passed", validation)


def apply_alignment_bundle_sync_success(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    validation: dict,
) -> dict:
    repository = context.repository
    repository.update_alignment_session(session_id, **alignment_bundle_sync_success_update_fields(validation))
    session = context.get_session(session_id)
    context.write_validation_log(session, validation)
    write_alignment_transcript_log(session)
    repository.append_alignment_event(session_id, "alignment_bundle_synced", validation)
    return session


def apply_alignment_bundle_sync_failure(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    validation: dict,
    finished_at: str,
) -> dict:
    repository = context.repository
    repository.update_alignment_session(
        session_id,
        **alignment_bundle_sync_failure_update_fields(validation, finished_at=finished_at),
    )
    session = context.get_session(session_id)
    context.write_validation_log(session, validation)
    write_alignment_transcript_log(session)
    repository.append_alignment_event(session_id, "alignment_bundle_sync_failed", validation)
    return alignment_bundle_sync_failure_result(session, validation)


def apply_alignment_import_failure(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    validation: dict,
    error: str,
) -> None:
    repository = context.repository
    repository.update_alignment_session(session_id, validation=validation, error_message=error)
    context.write_validation_log(context.get_session(session_id), validation)
    repository.append_alignment_event(
        session_id,
        "alignment_import_failed",
        alignment_import_failed_event_payload(error, validation),
    )


def apply_alignment_imported(
    context: AlignmentBundleLifecycleContext,
    session_id: str,
    *,
    bundle: dict,
    validation: dict,
) -> None:
    repository = context.repository
    repository.update_alignment_session(session_id, **alignment_imported_update_fields(bundle, validation))
    context.write_validation_log(context.get_session(session_id), validation)
    repository.append_alignment_event(session_id, "alignment_imported", alignment_imported_event_payload(bundle))


def apply_alignment_run_start_failed(
    repository: AlignmentBundleLifecycleRepository,
    session_id: str,
    *,
    bundle: dict,
    error: str,
) -> None:
    repository.update_alignment_session(session_id, error_message=error)
    repository.append_alignment_event(
        session_id,
        "alignment_run_start_failed",
        alignment_run_start_failed_event_payload(bundle, error),
    )


def apply_alignment_run_started(
    repository: AlignmentBundleLifecycleRepository,
    session_id: str,
    *,
    bundle: dict,
    run: dict,
) -> None:
    repository.update_alignment_session(session_id, status="running_loop", linked_run_id=run["id"])
    repository.append_alignment_event(
        session_id,
        "alignment_run_started",
        alignment_run_started_event_payload(bundle, run),
    )
