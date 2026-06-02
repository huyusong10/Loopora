from __future__ import annotations

from pathlib import Path

import pytest

from compacted_contract_support import (
    FakeAlignmentSessionProjectionRepository,
    session_access_context,
)
from loopora.service_alignment_session_projection import (
    get_alignment_session,
    latest_alignment_event_id,
    list_alignment_events,
    list_alignment_sessions,
)
from loopora.service_types import LooporaNotFoundError


ALIGNMENT_READY_EVENT_ID = 2


def test_alignment_session_access_projects_detail_and_checks_layout(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionProjectionRepository(
        [
            {
                "id": "align_1",
                "status": "running",
                "workdir": str(tmp_path),
                "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
                "transcript": [{"role": "user", "content": "Plan from Agent entry."}],
                "working_agreement": {},
            }
        ]
    )
    ensure_calls: list[str] = []

    session = get_alignment_session(session_access_context(repo, ensure_calls=ensure_calls), "align_1")

    assert ensure_calls == ["align_1"]
    assert session["layout_checked"] is True
    assert session["is_active"] is True
    assert session["agent_entry_review"]["missing_judgment_item_ids"] == ["task_scope"]
    assert session["agent_entry_launch"]["source"] == "agent_entry"
    assert session["agent_entry_launch"]["host_context_id"] == "thread:align_1"


def test_alignment_session_access_lists_summaries_and_validates_event_reads(tmp_path: Path) -> None:
    repo = FakeAlignmentSessionProjectionRepository(
        [
            {
                "id": "align_1",
                "status": "idle",
                "workdir": str(tmp_path),
                "bundle_path": str(tmp_path / "align_1" / "artifacts" / "bundle.yml"),
                "transcript": [{"role": "user", "content": "Use Authorization: Bearer SESSION_ACCESS_SECRET"}],
            }
        ],
        events_by_session={
            "align_1": [
                {"id": 1, "event_type": "alignment_started", "payload": {}},
                {"id": 2, "event_type": "alignment_ready", "payload": {}},
            ]
        },
    )
    context = session_access_context(repo)

    summaries = list_alignment_sessions(context, limit=5)
    events = list_alignment_events(context, "align_1", after_id=1, limit=10)
    latest_id = latest_alignment_event_id(context, "align_1")

    assert repo.list_limits == [5]
    assert summaries[0]["title"] == "Use Authorization: <secret omitted>"
    assert events == [{"id": ALIGNMENT_READY_EVENT_ID, "event_type": "alignment_ready", "payload": {}}]
    assert latest_id == ALIGNMENT_READY_EVENT_ID

    with pytest.raises(LooporaNotFoundError, match="unknown alignment session"):
        list_alignment_events(context, "missing")
