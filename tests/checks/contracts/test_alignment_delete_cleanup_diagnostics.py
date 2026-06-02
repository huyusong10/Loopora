from pathlib import Path

from alignment_delete_test_support import (
    FakeAlignmentDeleteRepository,
    alignment_delete_session,
    delete_alignment_with_defaults,
    delete_context,
)


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

    deleted = delete_alignment_with_defaults(context, session["id"])

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
