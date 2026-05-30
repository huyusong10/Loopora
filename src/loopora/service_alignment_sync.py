from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import BundleError, read_bundle_file_text
from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    alignment_bundle_missing_file_validation,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
    apply_alignment_bundle_sync_failure,
    apply_alignment_bundle_sync_success,
)
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.utils import utc_now


class AlignmentBundleTextLoader(Protocol):
    def __call__(self, session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]: ...


class AlignmentBundlePreviewBuilder(Protocol):
    def __call__(self, bundle: dict, *, source_path: str, validation: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentSyncContext:
    get_session: Callable[[str], dict]
    load_validated_bundle_text: AlignmentBundleTextLoader
    append_system_message: Callable[[str, str, str], dict]
    bundle_lifecycle_context: Callable[[], AlignmentBundleLifecycleContext]
    build_preview: AlignmentBundlePreviewBuilder
    now: Callable[[], str] = utc_now


def sync_alignment_bundle_from_file(
    context: AlignmentSyncContext,
    session_id: str,
    *,
    active_statuses: set[str],
) -> dict:
    session = context.get_session(session_id)
    if session["status"] in active_statuses:
        raise LooporaConflictError("cannot sync bundle while alignment session is active")
    if session["status"] not in {"idle", "ready", "failed"}:
        raise LooporaConflictError(f"cannot sync bundle in status {session['status']}")
    bundle_path = Path(session["bundle_path"])
    if not bundle_path.exists():
        validation = alignment_bundle_missing_file_validation(bundle_path, checked_at=context.now())
        return _record_alignment_bundle_sync_failure(context, session_id, validation)

    semantic_issues: list[str] = []
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        bundle, normalized_yaml = context.load_validated_bundle_text(session, raw_yaml, semantic_issues)
        bundle_path.write_text(normalized_yaml, encoding="utf-8")
    except (BundleError, LooporaError, OSError) as exc:
        validation = alignment_bundle_validation_failure(
            bundle_path,
            error=str(exc),
            semantic_issues=semantic_issues,
            checked_at=context.now(),
        )
        return _record_alignment_bundle_sync_failure(context, session_id, validation)

    validation = alignment_bundle_validation_success(
        bundle_path,
        checked_at=context.now(),
        normalized_yaml=normalized_yaml,
    )
    context.append_system_message(
        session_id,
        "已重新读取 bundle.yml，并校验通过。",
        "Reloaded bundle.yml and validation passed.",
    )
    session = apply_alignment_bundle_sync_success(
        context.bundle_lifecycle_context(),
        session_id,
        validation=validation,
    )
    preview = context.build_preview(
        bundle,
        source_path=str(bundle_path),
        validation=validation,
    )
    preview["session"] = session
    preview["yaml"] = normalized_yaml
    return preview


def _record_alignment_bundle_sync_failure(context: AlignmentSyncContext, session_id: str, validation: dict) -> dict:
    error = str(validation.get("error", "") or "bundle validation failed")
    context.append_system_message(
        session_id,
        f"重新读取 bundle.yml 失败：{error}",
        f"Failed to reload bundle.yml: {error}",
    )
    return apply_alignment_bundle_sync_failure(
        context.bundle_lifecycle_context(),
        session_id,
        validation=validation,
        finished_at=context.now(),
    )
