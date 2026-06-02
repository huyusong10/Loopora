from pathlib import Path

import pytest

from alignment_delete_test_support import (
    FakeAlignmentDeleteRepository,
    alignment_delete_session,
    delete_alignment_with_defaults,
    delete_context,
)
from loopora.service_types import LooporaConflictError


def test_delete_alignment_session_rejects_active_session(tmp_path: Path) -> None:
    session, session_dir = alignment_delete_session(tmp_path, status="running")
    repo = FakeAlignmentDeleteRepository()
    context, diagnostics, cleanup_marks = delete_context(repo, session)

    with pytest.raises(LooporaConflictError, match="cannot delete an active alignment session"):
        delete_alignment_with_defaults(context, session["id"])

    assert repo.delete_requests == []
    assert session_dir.exists()
    assert diagnostics == []
    assert cleanup_marks == []
