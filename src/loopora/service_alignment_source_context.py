from __future__ import annotations

from pathlib import Path
import re

from loopora.event_redaction import redact_sensitive_text, redact_sensitive_value


MODEL_VISIBLE_LOCAL_PATH_OMITTED = "<local path omitted>"
MODEL_VISIBLE_PATH_KEYS = frozenset({"spec_path", "source_bundle_path"})
MODEL_VISIBLE_PATH_CONTAINER_KEYS = frozenset({"artifact_paths"})
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^(?:[a-zA-Z]:[\\/]|\\\\)")


def bounded_alignment_file_text(path: Path, *, limit: int = 16000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return "Source file could not be read as UTF-8 text."
    except (OSError, ValueError):
        return "Source file could not be read."
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


def redact_alignment_model_context_value(value: object, *, key: str = "", parent_key: str = "") -> object:
    if isinstance(value, list):
        return [redact_alignment_model_context_value(item, parent_key=key) for item in value]
    if isinstance(value, dict):
        return {
            str(child_key): redact_alignment_model_context_value(item, key=str(child_key), parent_key=key)
            for child_key, item in value.items()
        }
    redacted = redact_sensitive_value(key, value)
    if key in MODEL_VISIBLE_PATH_KEYS or parent_key in MODEL_VISIBLE_PATH_CONTAINER_KEYS:
        return _model_visible_path_value(redacted)
    return redacted


def _model_visible_path_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    if not value.strip():
        return ""
    if _looks_like_absolute_local_path(value):
        return MODEL_VISIBLE_LOCAL_PATH_OMITTED
    return value


def _looks_like_absolute_local_path(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith(("/", "~/")) or bool(WINDOWS_ABSOLUTE_PATH_RE.match(text))
