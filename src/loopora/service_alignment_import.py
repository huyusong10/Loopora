from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.agent_entry_run_projection import AGENT_NATIVE_PREVIEW_ASYNC_START_ERROR
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_bundle_file_writes import write_bundle_text_atomically
from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
    apply_alignment_import_failure,
    apply_alignment_imported,
    apply_alignment_run_start_failed,
    apply_alignment_run_started,
)
from loopora.service_alignment_bundle_validation_payloads import ALIGNMENT_BUNDLE_MISSING_FILE_ERROR, ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
from loopora.service_alignment_requests import coerce_alignment_start_immediately
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError
from loopora.utils import utc_now


class AlignmentImportRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


class AlignmentBundleTextLoader(Protocol):
    def __call__(self, session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]: ...


@dataclass(frozen=True)
class AlignmentImportContext:
    repository: AlignmentImportRepository
    get_session: Callable[[str], dict]
    has_agent_entry_candidate: Callable[[str], bool]
    load_validated_bundle_text: AlignmentBundleTextLoader
    import_bundle_text: Callable[[str], dict]
    start_run: Callable[[str], dict]
    start_run_async: Callable[[str], None]
    bundle_lifecycle_context: Callable[[], AlignmentBundleLifecycleContext]
    now: Callable[[], str] = utc_now


def import_alignment_bundle(
    context: AlignmentImportContext,
    session_id: str,
    *,
    start_immediately: bool = True,
    execute_async: bool = True,
) -> dict:
    session = context.get_session(session_id)
    if session["status"] != "ready":
        raise LooporaConflictError(f"alignment session is not READY: {session['status']}")
    normalized_start = coerce_alignment_start_immediately(start_immediately)
    if normalized_start and execute_async and context.has_agent_entry_candidate(session_id):
        raise LooporaConflictError(AGENT_NATIVE_PREVIEW_ASYNC_START_ERROR)
    bundle_path = Path(session["bundle_path"])
    if not bundle_path.exists():
        raise LooporaNotFoundError(ALIGNMENT_BUNDLE_MISSING_FILE_ERROR)
    semantic_issues: list[str] = []
    raw_yaml: str | None = None
    normalized_write_started = False
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        _candidate_bundle, normalized_yaml = context.load_validated_bundle_text(
            session,
            raw_yaml,
            semantic_issues,
        )
        if normalized_yaml != raw_yaml:
            normalized_write_started = True
            write_bundle_text_atomically(bundle_path, normalized_yaml)
        bundle = context.import_bundle_text(normalized_yaml)
    except (BundleError, LooporaError, OSError) as exc:
        if raw_yaml is not None and normalized_write_started:
            _restore_alignment_import_candidate(bundle_path, raw_yaml)
        error = ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR if isinstance(exc, OSError) else str(exc)
        validation = alignment_bundle_validation_failure(
            bundle_path,
            error=error,
            semantic_issues=semantic_issues,
            checked_at=context.now(),
        )
        apply_alignment_import_failure(
            context.bundle_lifecycle_context(),
            session_id,
            validation=validation,
            error=error,
        )
        if isinstance(exc, LooporaError):
            raise
        raise LooporaError(error) from exc
    validation = alignment_bundle_validation_success(
        bundle_path,
        checked_at=context.now(),
        normalized_yaml=normalized_yaml,
    )
    apply_alignment_imported(
        context.bundle_lifecycle_context(),
        session_id,
        bundle=bundle,
        validation=validation,
    )
    redirect_url = f"/bundles/{bundle['id']}"
    if normalized_start:
        return _imported_alignment_start_result(context, session_id, bundle, execute_async=execute_async)
    if bundle.get("loop_id"):
        redirect_url = f"/loops/{bundle['loop_id']}"
    return {
        "session": context.get_session(session_id),
        "bundle": bundle,
        "loop": bundle.get("loop"),
        "run": None,
        "redirect_url": redirect_url,
    }


def _restore_alignment_import_candidate(bundle_path: Path, raw_yaml: str) -> None:
    with suppress(OSError):
        write_bundle_text_atomically(bundle_path, raw_yaml)


def _imported_alignment_start_result(
    context: AlignmentImportContext,
    session_id: str,
    bundle: dict,
    *,
    execute_async: bool,
) -> dict:
    try:
        run = context.start_run(bundle["loop_id"])
    except LooporaError as exc:
        apply_alignment_run_start_failed(context.repository, session_id, bundle=bundle, error=str(exc))
        raise
    if execute_async:
        dispatch_failure_result = _alignment_async_dispatch_failure_result(context, session_id, bundle, run)
        if dispatch_failure_result is not None:
            return dispatch_failure_result
    apply_alignment_run_started(context.repository, session_id, bundle=bundle, run=run)
    return {
        "session": context.get_session(session_id),
        "bundle": bundle,
        "loop": bundle.get("loop"),
        "run": run,
        "redirect_url": f"/runs/{run['id']}",
    }


def _alignment_async_dispatch_failure_result(
    context: AlignmentImportContext,
    session_id: str,
    bundle: dict,
    run: dict,
) -> dict | None:
    try:
        context.start_run_async(run["id"])
    except LooporaError as exc:
        apply_alignment_run_start_failed(context.repository, session_id, bundle=bundle, error=str(exc), run=run)
        if str(exc) != BACKGROUND_WORKER_START_ERROR:
            raise
        return {
            "session": context.get_session(session_id),
            "bundle": bundle,
            "loop": bundle.get("loop"),
            "run": run,
            "redirect_url": f"/runs/{run['id']}",
            "run_start_error": str(exc),
            "run_recovery": "retry_run_start",
        }
    return None
