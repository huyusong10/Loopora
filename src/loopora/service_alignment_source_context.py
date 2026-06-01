from __future__ import annotations

from pathlib import Path

from loopora.event_redaction import redact_sensitive_text, redact_sensitive_value


def bounded_alignment_file_text(path: Path, *, limit: int = 16000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return "Source file could not be read as UTF-8 text."
    except OSError as exc:
        return f"Source file could not be read: {exc}"
    text = redact_sensitive_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[Loopora truncated this source context for prompt size.]"


def alignment_transcript_source_summary(session: dict) -> list[dict]:
    entries = [entry for entry in (session.get("transcript") or []) if isinstance(entry, dict)]
    summary: list[dict] = []
    for entry in entries[-8:]:
        content = redact_sensitive_text(str(entry.get("content", "") or "").strip())
        if not content:
            continue
        summary.append(
            {
                "role": str(entry.get("role") or ""),
                "content": content[:600],
                "created_at": entry.get("created_at", ""),
            }
        )
    return summary


def redact_alignment_source_value(value: object, *, key: str = "") -> object:
    if isinstance(value, list):
        return [redact_alignment_source_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(child_key): redact_alignment_source_value(item, key=str(child_key))
            for child_key, item in value.items()
        }
    return redact_sensitive_value(key, value)
