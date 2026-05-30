from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import BundleError, read_bundle_file_text
from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
    apply_alignment_import_failure,
    apply_alignment_imported,
    apply_alignment_run_start_failed,
    apply_alignment_run_started,
)
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
        raise LooporaConflictError("agent-first Loop previews must be started from /loopora-run so the host Agent executes the run natively")
    bundle_path = Path(session["bundle_path"])
    if not bundle_path.exists():
        raise LooporaNotFoundError(f"alignment bundle does not exist: {bundle_path}")
    semantic_issues: list[str] = []
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        _candidate_bundle, normalized_yaml = context.load_validated_bundle_text(
            session,
            raw_yaml,
            semantic_issues,
        )
        bundle_path.write_text(normalized_yaml, encoding="utf-8")
        bundle = context.import_bundle_text(normalized_yaml)
    except (BundleError, LooporaError, OSError) as exc:
        error = str(exc)
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
    run = None
    redirect_url = f"/bundles/{bundle['id']}"
    if normalized_start:
        try:
            run = context.start_run(bundle["loop_id"])
            if execute_async:
                context.start_run_async(run["id"])
        except LooporaError as exc:
            apply_alignment_run_start_failed(context.repository, session_id, bundle=bundle, error=str(exc))
            raise
        apply_alignment_run_started(context.repository, session_id, bundle=bundle, run=run)
        redirect_url = f"/runs/{run['id']}"
    elif bundle.get("loop_id"):
        redirect_url = f"/loops/{bundle['loop_id']}"
    return {
        "session": context.get_session(session_id),
        "bundle": bundle,
        "loop": bundle.get("loop"),
        "run": run,
        "redirect_url": redirect_url,
    }
