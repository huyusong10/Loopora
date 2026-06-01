from __future__ import annotations

import json
from pathlib import Path

from loopora.event_redaction import redact_alignment_event_payload


def alignment_event_artifact_root(bundle_path: object) -> Path:
    path = Path(str(bundle_path))
    return path.parent.parent if path.parent.name == "artifacts" else path.parent


def append_alignment_event_artifact(bundle_path: object, event: dict) -> None:
    try:
        events_dir = alignment_event_artifact_root(bundle_path) / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        with (events_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(alignment_event_artifact_payload(event), ensure_ascii=False) + "\n")
    except OSError:
        return


def alignment_event_artifact_payload(event: dict) -> dict:
    payload = redact_alignment_event_payload(str(event.get("event_type") or ""), event.get("payload") or {})
    return {**event, "payload": payload}
