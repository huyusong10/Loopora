from __future__ import annotations

import re
from collections.abc import Collection


def alignment_needs_user_input(output: dict) -> bool:
    return output.get("needs_user_input") is True


def normalize_alignment_missing_items(
    raw_items: object,
    *,
    allowed_item_ids: Collection[str],
    limit: int = 12,
) -> list[str]:
    if not isinstance(raw_items, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        item = str(raw_item or "").strip()
        if item not in allowed_item_ids or item in seen:
            continue
        seen.add(item)
        items.append(item)
        if len(items) >= limit:
            break
    return items


def normalize_alignment_decision_options(raw_options: object) -> list[dict]:
    if not isinstance(raw_options, list):
        return []
    options: list[dict] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_options[:4], start=1):
        if not isinstance(item, dict):
            continue
        label = _alignment_text_snippet(item.get("label"), limit=80)
        description = _alignment_text_snippet(item.get("description"), limit=220)
        user_reply = _alignment_text_snippet(item.get("user_reply"), limit=260)
        if not label or not description or not user_reply:
            continue
        option_id = str(item.get("id") or f"option_{index}").strip()
        option_id = re.sub(r"[^A-Za-z0-9_.:-]+", "-", option_id).strip("-") or f"option_{index}"
        if option_id in seen_ids:
            option_id = f"{option_id}-{index}"
        seen_ids.add(option_id)
        options.append(
            {
                "id": option_id,
                "label": label,
                "description": description,
                "recommended": item.get("recommended") is True,
                "user_reply": user_reply,
            }
        )
    return options


def alignment_has_recommended_decision_options(output: dict) -> bool:
    options = normalize_alignment_decision_options(output.get("decision_options"))
    return alignment_decision_options_are_visible(options)


def alignment_decision_options_are_visible(options: list[dict]) -> bool:
    recommended_count = sum(option.get("recommended") is True for option in options)
    return len(options) >= 2 and recommended_count == 1


def _alignment_text_snippet(value: object, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
