from __future__ import annotations

from pathlib import Path

from loopora.db_shared import logger
from loopora.diagnostics import log_exception
from loopora.run_artifacts import RunArtifactLayout


def mirror_run_event_record(run: object, record: dict, *, run_id: str, role: str | None, event_type: str) -> None:
    if not run:
        return
    try:
        layout = RunArtifactLayout(Path(run["runs_dir"]))
        from loopora import db as db_module

        db_module.append_jsonl_with_mirrors(
            layout.timeline_events_path,
            record,
            mirror_paths=[layout.legacy_events_path],
        )
    except Exception:  # noqa: BLE001 - local run event mirrors are best-effort after the DB event is durable.
        log_exception(
            logger,
            "db.run_event.mirror_failed",
            "Failed to mirror run event to events.jsonl",
            run_id=run_id,
            role=role,
            event_type=event_type,
            runs_dir=run["runs_dir"],
        )
