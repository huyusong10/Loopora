from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id

from loop_event_core_test_support import create_loop


LOOP_ARCHIVE_SOURCE_SEQUENCE = 4


def test_loop_delete_archives_loop_stream_before_removing_legacy_record(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    create_loop(
        repository,
        tmp_path,
        {
            "id": "loop_archive_event",
            "name": "Loop Archive Event",
            "task": "Archive me.",
        },
    )

    assert repository.delete_loop("loop_archive_event") is True
    assert repository.get_loop("loop_archive_event") is None
    events = repository.list_domain_events(loop_stream_id("loop_archive_event"))

    assert [event.event_type for event in events] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopArchived",
    ]
    assert events[-1].payload == {"loop_id": "loop_archive_event", "reason": "deleted"}
    cached = repository.get_projection_record("loop_definition", "loop_archive_event")
    assert cached["source_sequence"] == LOOP_ARCHIVE_SOURCE_SEQUENCE
    assert cached["payload"]["status"] == "archived"
