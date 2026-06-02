import logging
from pathlib import Path

from loopora.service_alignment_delete import AlignmentDeleteContext, delete_alignment_session

ACTIVE_ALIGNMENT_STATUSES = {"running", "validating", "repairing"}


class FakeAlignmentDeleteRepository:
    def __init__(self, *, deleted: bool = True) -> None:
        self.deleted = deleted
        self.delete_requests: list[str] = []

    def delete_alignment_session(self, session_id: str) -> bool:
        self.delete_requests.append(session_id)
        return self.deleted


def delete_context(
    repo: FakeAlignmentDeleteRepository,
    session: dict,
    *,
    remove_tree=None,
) -> tuple[AlignmentDeleteContext, list[dict], list[dict]]:
    diagnostics: list[dict] = []
    cleanup_marks: list[dict] = []

    def get_session(session_id: str) -> dict:
        assert session_id == session["id"]
        return dict(session)

    def append_local_diagnostic_event(session_payload: dict, event_type: str, payload: dict[str, object]) -> None:
        diagnostics.append({"session": session_payload, "event_type": event_type, "payload": payload})

    def mark_local_asset_cleanup_by_path(path: Path, *, operation: str, owner_id: str) -> None:
        cleanup_marks.append({"path": path, "operation": operation, "owner_id": owner_id})

    context = AlignmentDeleteContext(
        repository=repo,
        get_session=get_session,
        append_local_diagnostic_event=append_local_diagnostic_event,
        mark_local_asset_cleanup_by_path=mark_local_asset_cleanup_by_path,
        **({"remove_tree": remove_tree} if remove_tree is not None else {}),
    )
    return context, diagnostics, cleanup_marks


def alignment_delete_session(
    tmp_path: Path,
    *,
    session_id: str = "align_delete",
    status: str = "idle",
    root: Path | None = None,
) -> tuple[dict, Path]:
    root = root or tmp_path / ".loopora" / "alignment_sessions" / session_id
    bundle_path = root / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {
        "id": session_id,
        "status": status,
        "bundle_path": str(bundle_path),
    }, root


def delete_alignment_with_defaults(context: AlignmentDeleteContext, session_id: str) -> bool:
    return delete_alignment_session(
        context,
        session_id,
        active_statuses=ACTIVE_ALIGNMENT_STATUSES,
        logger=logging.getLogger("tests.alignment.delete"),
    )


__all__ = [
    "FakeAlignmentDeleteRepository",
    "alignment_delete_session",
    "delete_alignment_with_defaults",
    "delete_context",
]
