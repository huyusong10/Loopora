from __future__ import annotations


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


def non_bool_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def clip_inline(text: str, limit: int) -> str:
    return clip(" ".join(str(text or "").split()), limit)
