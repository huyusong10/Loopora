import logging
from pathlib import Path

import pytest

from loopora.service_alignment_delete import AlignmentDeleteContext, delete_alignment_session
from loopora.service_types import LooporaConflictError


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


def alignment_delete_session(tmp_path: Path, *, session_id: str = "align_delete", status: str = "idle", root: Path | None = None) -> tuple[dict, Path]:
    root = root or tmp_path / ".loopora" / "alignment_sessions" / session_id
    bundle_path = root / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    return {
        "id": session_id,
        "status": status,
        "bundle_path": str(bundle_path),
    }, root


def test_delete_alignment_session_removes_safe_inactive_session_dir(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path)
    context, diagnostics, cleanup_marks = delete_context(FakeAlignmentDeleteRepository(), session)

    deleted = delete_alignment_session(
        context,
        session["id"],
        active_statuses={"running", "validating", "repairing"},
        logger=logging.getLogger(__name__),
    )

    assert deleted is True
    assert not session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == [{"path": session_dir, "operation": "alignment_session_delete", "owner_id": session["id"]}]


def test_delete_alignment_session_rejects_active_session(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path, status="running")
    repo = FakeAlignmentDeleteRepository()
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    with pytest.raises(LooporaConflictError, match="cannot delete an active alignment session"):
        delete_alignment_session(
            context,
            session["id"],
            active_statuses={"running", "validating", "repairing"},
            logger=logging.getLogger(__name__),
        )

    assert repo.delete_requests == []
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []


@pytest.mark.parametrize(
    "root_parts",
    [
        (".loopora", "alignment_sessions", "other_session"),
        ("not_alignment_sessions", "align_delete"),
    ],
)
def test_delete_alignment_session_does_not_cleanup_unsafe_artifact_roots(tmp_path: Path, root_parts: tuple[str, ...]) -> None:
    session, session_dir = alignment_delete_session(tmp_path, root=tmp_path.joinpath(*root_parts))
    repo = FakeAlignmentDeleteRepository()
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    deleted = delete_alignment_session(
        context,
        session["id"],
        active_statuses={"running", "validating", "repairing"},
        logger=logging.getLogger(__name__),
    )

    assert deleted is True
    assert repo.delete_requests == [session["id"]]
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []


def test_delete_alignment_session_skips_cleanup_when_repository_delete_misses(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path)
    repo = FakeAlignmentDeleteRepository(deleted=False)
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    deleted = delete_alignment_session(
        context,
        session["id"],
        active_statuses={"running", "validating", "repairing"},
        logger=logging.getLogger(__name__),
    )

    assert deleted is False
    assert repo.delete_requests == [session["id"]]
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []


def test_delete_alignment_session_records_cleanup_diagnostic_callback(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path)

    def fail_remove_tree(path: Path, _logger, *, operation: str, owner_id: str, on_failure) -> bool:
        assert path == session_dir
        on_failure(
            {
                "operation": operation,
                "resource_type": "path",
                "resource_id": str(path),
                "owner_id": owner_id,
                "error_type": "OSError",
                "error_message": "alignment dir locked",
            }
        )
        return False

    context, diagnostics, cleanup_marks = delete_context(
        FakeAlignmentDeleteRepository(),
        session,
        remove_tree=fail_remove_tree,
    )

    deleted = delete_alignment_session(
        context,
        session["id"],
        active_statuses={"running", "validating", "repairing"},
        logger=logging.getLogger(__name__),
    )

    assert deleted is True
    assert diagnostics == [
        {
            "session": session,
            "event_type": "alignment_session_cleanup_failed",
            "payload": {
                "operation": "alignment_session_delete",
                "resource_type": "path",
                "resource_id": str(session_dir),
                "owner_id": session["id"],
                "error_type": "OSError",
                "error_message": "alignment dir locked",
            },
        }
    ]
    assert cleanup_marks == [{"path": session_dir, "operation": "alignment_session_delete", "owner_id": session["id"]}]
