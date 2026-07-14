from __future__ import annotations

from collections.abc import Mapping


ALIGNMENT_PROMPT_TASK_ANCHOR_CHAR_LIMIT = 16_000
ALIGNMENT_PROMPT_RECENT_ENTRY_CHAR_LIMIT = 6_000
ALIGNMENT_PROMPT_RECENT_ENTRY_LIMIT = 10
ALIGNMENT_PROMPT_RECENT_TOTAL_CHAR_LIMIT = 32_000
ALIGNMENT_PROMPT_TRANSCRIPT_TRUNCATION_MARKER = "\n[... content omitted from model context ...]\n"


def alignment_prompt_transcript_projection(raw_transcript: object) -> list[dict]:
    raw_entries = raw_transcript if isinstance(raw_transcript, list) else []
    indexed_entries = [(index, entry) for index, entry in enumerate(raw_entries) if isinstance(entry, Mapping)]
    task_anchor_index = next(
        (index for index, entry in indexed_entries if entry.get("role") == "user" and str(entry.get("content") or "").strip()),
        None,
    )

    projected_by_index: dict[int, dict] = {}
    content_truncated = False
    if task_anchor_index is not None:
        task_anchor_entry = next(entry for index, entry in indexed_entries if index == task_anchor_index)
        projected, was_truncated = _alignment_prompt_transcript_entry(
            task_anchor_entry,
            content_limit=ALIGNMENT_PROMPT_TASK_ANCHOR_CHAR_LIMIT,
        )
        projected_by_index[task_anchor_index] = projected
        content_truncated = was_truncated

    recent_indices: list[int] = []
    remaining_chars = ALIGNMENT_PROMPT_RECENT_TOTAL_CHAR_LIMIT
    for index, entry in reversed(indexed_entries):
        if index == task_anchor_index:
            continue
        if len(recent_indices) >= ALIGNMENT_PROMPT_RECENT_ENTRY_LIMIT or remaining_chars < 256:
            break
        projected, was_truncated = _alignment_prompt_transcript_entry(
            entry,
            content_limit=min(ALIGNMENT_PROMPT_RECENT_ENTRY_CHAR_LIMIT, remaining_chars),
        )
        projected_by_index[index] = projected
        recent_indices.append(index)
        remaining_chars -= len(str(projected.get("content") or ""))
        content_truncated = content_truncated or was_truncated

    included_indices = sorted(projected_by_index)
    omitted_entries = max(0, len(raw_entries) - len(included_indices))
    projection = [projected_by_index[index] for index in included_indices]
    if omitted_entries or content_truncated:
        projection.insert(
            0,
            {
                "role": "context",
                "kind": "transcript_projection",
                "total_entries": len(raw_entries),
                "included_entries": len(included_indices),
                "omitted_entries": omitted_entries,
                "task_anchor_retained": task_anchor_index is not None,
                "content_truncated": content_truncated,
            },
        )
    return projection


def _alignment_prompt_transcript_entry(entry: Mapping[str, object], *, content_limit: int) -> tuple[dict, bool]:
    content = str(entry.get("content") or "")
    bounded_content, content_truncated = _alignment_bounded_prompt_text(content, limit=content_limit)
    projected: dict[str, object] = {
        "role": "user" if entry.get("role") == "user" else "assistant",
        "content": bounded_content,
    }
    created_at = str(entry.get("created_at") or "").strip()
    if created_at:
        projected["created_at"] = created_at[:80]
    missing_items = entry.get("missing_items")
    if isinstance(missing_items, list):
        normalized_missing = [str(item).strip()[:80] for item in missing_items[:12] if str(item).strip()]
        if normalized_missing:
            projected["missing_items"] = normalized_missing
    if content_truncated:
        projected["content_truncated"] = True
        projected["original_content_chars"] = len(content)
    return projected, content_truncated


def _alignment_bounded_prompt_text(value: str, *, limit: int) -> tuple[str, bool]:
    text = str(value or "")
    if len(text) <= limit:
        return text, False
    marker = ALIGNMENT_PROMPT_TRANSCRIPT_TRUNCATION_MARKER
    available = max(0, limit - len(marker))
    leading_chars = (available * 2) // 3
    trailing_chars = available - leading_chars
    bounded = text[:leading_chars] + marker
    if trailing_chars:
        bounded += text[-trailing_chars:]
    return bounded, True
