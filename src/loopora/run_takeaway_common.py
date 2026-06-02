from __future__ import annotations

import json
import re
from pathlib import Path

from loopora.branding import strip_run_summary_title
from loopora.structured_numbers import structured_non_negative_int
from loopora.strategy_source import (
    STRATEGY_SOURCE_ARCHETYPES,
    normalize_strategy_role_display_name,
    strategy_archetype_display_name,
)

LEGACY_RUNTIME_ROLE_TO_ARCHETYPE = {
    "generator": "builder",
    "tester": "inspector",
    "verifier": "gatekeeper",
    "challenger": "guide",
}


def display_iter(iter_value: object | None) -> int | None:
    if iter_value is None:
        return None
    normalized = _int_value(iter_value, default=None)
    if normalized is None:
        return None
    return normalized + 1


def strip_markdown(value: str | None) -> str:
    text = str(value or "")
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()


def truncate_text(value: str, max_length: int = 140) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def summary_excerpt(summary_md: str | None) -> str:
    text = strip_markdown(summary_md)
    text = strip_run_summary_title(text)
    return truncate_text(text, max_length=170) if text else ""


def safe_read_json_file(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def clean_takeaway_text(value: object, *, max_length: int = 240) -> str:
    if not isinstance(value, str):
        return ""
    text = truncate_text(strip_markdown(value.strip()), max_length=max_length)
    return text.strip()


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def display_role_name(name: object, *, archetype: object = "", runtime_role: object = "") -> str:
    cleaned_name = _string_value(name)
    cleaned_runtime = _string_value(runtime_role).lower()
    cleaned_archetype = _string_value(archetype).lower() or LEGACY_RUNTIME_ROLE_TO_ARCHETYPE.get(cleaned_runtime, "")
    normalized_name = normalize_strategy_role_display_name(cleaned_name, cleaned_archetype)
    if normalized_name:
        return normalized_name
    if cleaned_archetype in STRATEGY_SOURCE_ARCHETYPES:
        return strategy_archetype_display_name(cleaned_archetype, locale="en")
    return cleaned_name or cleaned_runtime or "-"


def normalize_takeaway_status(status: object) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"passed", "completed", "blocked", "failed", "running", "advisory", "pending"}:
        return normalized
    if normalized in {"complete", "succeeded", "success"}:
        return "completed"
    if normalized in {"queued", "waiting", "idle"}:
        return "pending"
    return "pending"


def _int_value(value: object, *, default: int | None) -> int | None:
    if default is None:
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return None
    return structured_non_negative_int(value, default=default)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
