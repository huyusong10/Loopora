from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def combine_event_redaction_reports(
    *,
    fix: bool,
    db_events: dict,
    timeline_files: dict,
    alignment_db_events: dict,
    alignment_event_files: dict,
) -> dict:
    reports = (db_events, timeline_files, alignment_db_events, alignment_event_files)
    return {
        "mode": "fix" if fix else "dry-run",
        "db_events": db_events,
        "timeline_files": timeline_files,
        "alignment_db_events": alignment_db_events,
        "alignment_event_files": alignment_event_files,
        "fixed": sum(int(report["fixed"]) for report in reports),
        "suspect": sum(int(report["suspect"]) for report in reports),
        "unfixable": [item for report in reports for item in report["unfixable"]],
    }


def redaction_changed(current: object, redacted: object) -> bool:
    return _canonical_json(redacted) != _canonical_json(current)


def event_redaction_sample(
    source: str,
    event: dict,
    redacted: dict,
    *,
    path: Path | None = None,
    line: int | None = None,
) -> dict:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    changed_keys = sorted({str(key) for key in set(payload) | set(redacted) if payload.get(key) != redacted.get(key)})
    sample: dict[str, Any] = {
        "source": source,
        "event_id": event.get("id"),
        "run_id": event.get("run_id"),
        "session_id": event.get("session_id"),
        "event_type": event.get("event_type"),
        "changed_keys": changed_keys,
    }
    if path is not None:
        sample["path"] = str(path)
    if line is not None:
        sample["line"] = line
    return sample


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
