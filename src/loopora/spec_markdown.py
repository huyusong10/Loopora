from __future__ import annotations

import re
from typing import Any

from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.strategy_source import (
    normalize_strategy_role_display_name,
    strategy_archetype_display_name,
)

REQUIRED_SECTIONS = ["Task"]
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
BULLET_ITEM_PATTERN = re.compile(r"^[-*]\s+(.+?)\s*$", re.MULTILINE)
ROLE_NOTE_HEADING_PATTERN = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
ROLE_NOTES_SUFFIX_RE = re.compile(r"\s+notes\s*$", re.IGNORECASE)
LIST_SECTIONS = {
    "Success Surface": "success_surface",
    "Fake Done": "fake_done_states",
    "Evidence Preferences": "evidence_preferences",
}
TEXT_SECTIONS = {
    "Residual Risk": "residual_risk",
}


class SpecError(ValueError):
    """Raised when a Markdown spec cannot be compiled."""


def compile_markdown_spec(markdown_text: str) -> dict:
    cleaned_markdown = _strip_html_comments(markdown_text)
    sections = _split_sections(cleaned_markdown)
    _reject_legacy_sections(sections)
    missing = [section for section in REQUIRED_SECTIONS if not sections.get(section, "").strip()]
    if missing:
        raise SpecError(f"missing top-level sections: {', '.join(missing)}")

    done_when_section = sections.get("Done When", "")
    checks = _extract_done_when_checks(done_when_section)
    if done_when_section.strip() and not checks:
        raise SpecError("`# Done When` must contain at least one top-level bullet item")
    role_notes = _extract_role_notes(sections.get("Role Notes", ""))
    list_sections: dict[str, list[str]] = {}
    for heading, field_name in LIST_SECTIONS.items():
        values = _extract_bullet_list(sections.get(heading, ""), heading=heading)
        list_sections[field_name] = values
    text_sections = {
        field_name: sections.get(heading, "").strip()
        for heading, field_name in TEXT_SECTIONS.items()
    }

    compiled_checks = []
    for index, check in enumerate(checks, start=1):
        compiled_checks.append(
            {
                "id": f"check_{index:03d}",
                "title": check["title"],
                "details": check["body"],
                "when": check["when"],
                "expect": check["expect"],
                "fail_if": check["fail_if"],
                "source": "specified",
            }
        )

    compiled = {
        "goal": sections["Task"].strip(),
        "constraints": sections.get("Guardrails", "").strip(),
        "checks": compiled_checks,
        "check_mode": "specified" if compiled_checks else "auto_generated",
        "role_notes": role_notes,
        **list_sections,
        **text_sections,
        "raw_sections": {key: value.strip() for key, value in sections.items()},
    }
    return with_coverage_targets(compiled)


def resolve_role_note(compiled_spec: dict[str, Any], *, role_name: str, archetype: str | None = None) -> str:
    role_notes = compiled_spec.get("role_notes")
    if not isinstance(role_notes, dict):
        return ""
    normalized_name = normalize_strategy_role_display_name(role_name, archetype=archetype) or str(role_name or "").strip()
    exact_candidates = [candidate.lower() for candidate in (normalized_name, str(role_name or "").strip()) if candidate]
    for candidate in exact_candidates:
        if candidate in role_notes:
            return str(role_notes[candidate]).strip()
    if archetype:
        archetype_label = strategy_archetype_display_name(archetype, locale="en").lower()
        if archetype_label in role_notes:
            return str(role_notes[archetype_label]).strip()
    return ""


def _split_sections(markdown_text: str) -> dict[str, str]:
    pattern = re.compile(r"^# (.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(markdown_text))
    sections: dict[str, str] = {}
    duplicate_sections: list[str] = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        if name in sections and name not in duplicate_sections:
            duplicate_sections.append(name)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        sections[name] = markdown_text[start:end].strip("\r\n")
    if duplicate_sections:
        raise SpecError(f"duplicate top-level sections: {', '.join(duplicate_sections)}")
    return sections


def _strip_html_comments(markdown_text: str) -> str:
    return HTML_COMMENT_PATTERN.sub("", markdown_text)


def _extract_done_when_checks(section_text: str) -> list[dict[str, str]]:
    matches = list(BULLET_ITEM_PATTERN.finditer(section_text))
    checks: list[dict[str, str]] = []
    for index, match in enumerate(matches, start=1):
        body = match.group(1).strip()
        title = _short_check_title(body, index=index)
        checks.append(
            {
                "title": title,
                "body": body,
                "when": "Someone evaluates the latest workspace state against the run contract.",
                "expect": body,
                "fail_if": f"The workspace still does not satisfy this outcome: {body}",
            }
        )
    return checks


def _extract_bullet_list(section_text: str, *, heading: str) -> list[str]:
    matches = list(BULLET_ITEM_PATTERN.finditer(section_text))
    if section_text.strip() and not matches:
        raise SpecError(f"`# {heading}` must contain at least one top-level bullet item")
    return [match.group(1).strip() for match in matches]


def _short_check_title(body: str, *, index: int) -> str:
    clean = re.sub(r"\s+", " ", body).strip(" .")
    if not clean:
        return f"Done When item {index}"
    words = clean.split(" ")
    if len(words) <= 8:
        return clean
    return " ".join(words[:8]).rstrip(" ,.;:") + "..."


def _extract_role_notes(section_text: str) -> dict[str, str]:
    matches = list(ROLE_NOTE_HEADING_PATTERN.finditer(section_text))
    if section_text.strip() and not matches:
        raise SpecError("`# Role Notes` must use `## <Role Name> Notes` subheadings")
    notes: dict[str, str] = {}
    duplicate_notes: list[str] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_text)
        body = section_text[start:end].strip()
        if not body:
            continue
        normalized_title = _normalize_role_note_heading(title)
        if not normalized_title:
            raise SpecError("role note subheadings must look like `## <Role Name> Notes`")
        if normalized_title in notes and normalized_title not in duplicate_notes:
            duplicate_notes.append(normalized_title)
        notes[normalized_title] = body
    if duplicate_notes:
        raise SpecError(f"duplicate role note sections: {', '.join(duplicate_notes)}")
    return notes


def _normalize_role_note_heading(title: str) -> str:
    trimmed = str(title or "").strip()
    without_suffix = ROLE_NOTES_SUFFIX_RE.sub("", trimmed).strip()
    if not without_suffix or without_suffix == trimmed:
        return ""
    return without_suffix.lower()


def _reject_legacy_sections(sections: dict[str, str]) -> None:
    legacy = [name for name in ("Goal", "Checks", "Constraints") if name in sections]
    if legacy:
        raise SpecError(
            "legacy spec headings are no longer supported; use `# Task`, `# Done When`, `# Guardrails`, "
            "`# Success Surface`, `# Fake Done`, `# Evidence Preferences`, `# Residual Risk`, and `# Role Notes`"
        )
