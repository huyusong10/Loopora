from pathlib import Path

import pytest

from alignment_delete_test_support import (
    FakeAlignmentDeleteRepository,
    alignment_delete_session,
    delete_alignment_with_defaults,
    delete_context,
)


def test_delete_alignment_session_removes_safe_inactive_session_dir(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path)
    context, diagnostics, cleanup_marks = delete_context(FakeAlignmentDeleteRepository(), session)

    deleted = delete_alignment_with_defaults(context, session["id"])

    assert deleted is True
    assert not session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == [{"path": session_dir, "operation": "alignment_session_delete", "owner_id": session["id"]}]


@pytest.mark.parametrize(
    "root_parts",
    [
        (".loopora", "alignment_sessions", "other_session"),
        ("not_alignment_sessions", "align_delete"),
    ],
)
def test_delete_alignment_session_does_not_cleanup_unsafe_artifact_roots(
    tmp_path: Path,
    root_parts: tuple[str, ...],
) -> None:
    session, session_dir = alignment_delete_session(tmp_path, root=tmp_path.joinpath(*root_parts))
    repo = FakeAlignmentDeleteRepository()
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    deleted = delete_alignment_with_defaults(context, session["id"])

    assert deleted is True
    assert repo.delete_requests == [session["id"]]
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []


def test_delete_alignment_session_skips_cleanup_when_repository_delete_misses(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path)
    repo = FakeAlignmentDeleteRepository(deleted=False)
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    deleted = delete_alignment_with_defaults(context, session["id"])

    assert deleted is False
    assert repo.delete_requests == [session["id"]]
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []
