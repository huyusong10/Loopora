from __future__ import annotations

from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.service_alignment_artifacts import alignment_session_root
from loopora.service_cleanup_diagnostics import best_effort_rmtree
from loopora.service_types import LooporaConflictError


class AlignmentDeleteRepository(Protocol):
    def delete_alignment_session(self, session_id: str) -> bool: ...


class AlignmentLocalDiagnosticAppender(Protocol):
    def __call__(self, session: dict, event_type: str, payload: dict[str, object]) -> None: ...


class AlignmentLocalAssetCleanupMarker(Protocol):
    def __call__(self, path: Path, *, operation: str, owner_id: str) -> None: ...


class AlignmentSessionTreeRemover(Protocol):
    def __call__(
        self,
        path: Path,
        logger,
        *,
        operation: str,
        owner_id: str,
        on_failure: Callable[[dict[str, object]], object],
    ) -> object: ...


def remove_alignment_session_tree(
    path: Path,
    logger,
    *,
    operation: str,
    owner_id: str,
    on_failure: Callable[[dict[str, object]], object],
) -> bool:
    return best_effort_rmtree(
        path,
        logger,
        operation=operation,
        owner_id=owner_id,
        on_failure=on_failure,
    )


@dataclass(frozen=True)
class AlignmentDeleteContext:
    repository: AlignmentDeleteRepository
    get_session: Callable[[str], dict]
    append_local_diagnostic_event: AlignmentLocalDiagnosticAppender
    mark_local_asset_cleanup_by_path: AlignmentLocalAssetCleanupMarker
    remove_tree: AlignmentSessionTreeRemover = remove_alignment_session_tree


def delete_alignment_session(
    context: AlignmentDeleteContext,
    session_id: str,
    *,
    active_statuses: Collection[str],
    logger,
) -> bool:
    session = context.get_session(session_id)
    if session["status"] in active_statuses:
        raise LooporaConflictError("cannot delete an active alignment session")

    session_dir = alignment_session_root(session)
    deleted = context.repository.delete_alignment_session(session_id)
    if deleted and _is_safe_alignment_session_cleanup_target(session_dir, session_id):
        context.remove_tree(
            session_dir,
            logger,
            operation="alignment_session_delete",
            owner_id=session_id,
            on_failure=lambda payload: context.append_local_diagnostic_event(
                session,
                "alignment_session_cleanup_failed",
                payload,
            ),
        )
        context.mark_local_asset_cleanup_by_path(
            session_dir,
            operation="alignment_session_delete",
            owner_id=session_id,
        )
    return deleted


def _is_safe_alignment_session_cleanup_target(session_dir: Path, session_id: str) -> bool:
    return session_dir.name == session_id and session_dir.parent.name == "alignment_sessions"
