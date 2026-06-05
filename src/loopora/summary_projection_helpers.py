from __future__ import annotations

from loopora.structured_numbers import structured_optional_non_negative_int


def set_summary_text(summary: dict[str, object], key: str, value: object) -> None:
    text = str(value or "").strip()
    if text:
        summary[key] = text


def set_summary_list(summary: dict[str, object], key: str, value: object) -> None:
    items = [str(item).strip() for item in list(value or []) if str(item).strip()] if isinstance(value, list) else []
    if items:
        summary[key] = items


def set_summary_mapping(summary: dict[str, object], key: str, value: object) -> None:
    if isinstance(value, dict) and value:
        summary[key] = value


def set_summary_before(summary: dict[str, object], key: str, value: object, before_key: str) -> None:
    if value in ("", [], {}, None):
        summary.pop(key, None)
        return
    summary.pop(key, None)
    if before_key not in summary:
        summary[key] = value
        return
    items = list(summary.items())
    summary.clear()
    inserted = False
    for existing_key, existing_value in items:
        if existing_key == before_key:
            summary[key] = value
            inserted = True
        summary[existing_key] = existing_value
    if not inserted:
        summary[key] = value


def non_bool_int(value: object) -> int | None:
    return structured_optional_non_negative_int(value)


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def clip_inline(text: str, limit: int) -> str:
    return clip(" ".join(str(text or "").split()), limit)
