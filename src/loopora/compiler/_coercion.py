from __future__ import annotations

from collections.abc import Mapping


def integer(value: object, *, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def mapping_list(value: object) -> list[Mapping[str, object]]:
    return [item for item in list(value or []) if isinstance(item, Mapping)]


def strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def text(value: object, *, fallback: str = "") -> str:
    result = str(value or "").strip()
    return result or fallback
