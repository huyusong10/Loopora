from __future__ import annotations

import fnmatch

from loopora.dev_check_changed_files import strip_current_dir_prefix
from loopora.dev_check_guides import FOCUSED_CHECK_GUIDES, FocusedCheckGuide
from loopora.service_types import LooporaError

DEFAULT_FOCUSED_SELECTION = "recommended"


def focused_check_selection_choices() -> tuple[str, ...]:
    return (DEFAULT_FOCUSED_SELECTION, "all", *(guide.id for guide in FOCUSED_CHECK_GUIDES))


def focused_check_selection_help() -> str:
    choices = ", ".join(focused_check_selection_choices())
    return (
        "Run focused checks selected from changed files, all guides, or one or more guide ids. "
        f"Choices: {choices}. Repeat --focused, comma-separate, or quote space-separated guide ids."
    )


def listed_focused_guide(guide: FocusedCheckGuide) -> dict[str, object]:
    return {
        "id": guide.id,
        "label": guide.label,
        "when": guide.when,
        "command": guide.command,
        "evidence_type": guide.evidence_type,
        "path_patterns": list(guide.path_patterns),
    }


def listed_focused_step(guide: dict[str, object]) -> dict[str, object]:
    guide_id = str(guide.get("id") or "").strip()
    return {
        "id": f"focused:{guide_id}" if guide_id else "focused",
        "guide_id": guide_id,
        "label": guide.get("label"),
        "command": guide.get("command"),
        "evidence_type": guide.get("evidence_type"),
        "status": "listed",
    }


def selected_focused_guides(
    selection: str,
    *,
    focused_guides: list[dict[str, object]],
    recommended_guides: list[dict[str, object]],
) -> list[dict[str, object]]:
    tokens = focused_selection_tokens(selection)
    if not tokens:
        return []
    selected: list[dict[str, object]] = []
    by_id = {str(guide.get("id") or ""): guide for guide in focused_guides}
    expected = ", ".join(focused_check_selection_choices())
    for token in tokens:
        if token == DEFAULT_FOCUSED_SELECTION:
            selected.extend(recommended_guides)
        elif token == "all":
            selected.extend(focused_guides)
        elif token in by_id:
            selected.append(by_id[token])
        else:
            raise LooporaError(f"unsupported focused check guide: {token!r}. Expected one of: {expected}")
    return dedupe_focused_guides(selected)


def focused_selection_tokens(selection: str) -> list[str]:
    return [token for token in selection.replace(",", " ").split() if token]


def focused_ran_tokens(values: list[str] | None) -> tuple[str, ...]:
    return tuple(dedupe_text(token for value in list(values or []) for token in str(value or "").replace(",", " ").split() if token))


def dedupe_text(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def dedupe_focused_guides(guides: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for guide in guides:
        guide_id = str(guide.get("id") or "")
        if not guide_id or guide_id in seen:
            continue
        seen.add(guide_id)
        deduped.append(guide)
    return deduped


def focused_guide_ids(guides: list[dict[str, object]]) -> list[str]:
    return [guide_id for guide in guides if (guide_id := str(guide.get("id") or "").strip())]


def recommended_focused_guides(focused_guides: list[dict[str, object]], changed_files: list[str]) -> list[dict[str, object]]:
    recommendations: list[dict[str, object]] = []
    for guide in focused_guides:
        patterns = [str(pattern) for pattern in list(guide.get("path_patterns") or [])]
        matched_files = [path for path in changed_files if any(path_matches_pattern(path, pattern) for pattern in patterns)]
        if matched_files:
            visible_matches = matched_files[:12]
            recommendations.append(
                {
                    **guide,
                    "matched_files": visible_matches,
                    "matched_file_count": len(matched_files),
                    "omitted_matched_file_count": len(matched_files) - len(visible_matches),
                }
            )
    return recommendations


def unmatched_changed_files(focused_guides: list[dict[str, object]], changed_files: list[str]) -> list[str]:
    patterns = [str(pattern) for guide in focused_guides for pattern in list(guide.get("path_patterns") or [])]
    return [path for path in changed_files if not any(path_matches_pattern(path, pattern) for pattern in patterns)]


def path_matches_pattern(path: str, pattern: str) -> bool:
    normalized_path = strip_current_dir_prefix(path.replace("\\", "/"))
    normalized_pattern = strip_current_dir_prefix(pattern.replace("\\", "/"))
    if not normalized_pattern:
        return False
    if normalized_pattern.endswith("/"):
        return normalized_path.startswith(normalized_pattern)
    return (
        normalized_path == normalized_pattern
        or normalized_path.startswith(normalized_pattern)
        or fnmatch.fnmatch(
            normalized_path,
            normalized_pattern,
        )
    )
