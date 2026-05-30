from __future__ import annotations

from pathlib import Path

from loopora.markdown_tools import render_safe_markdown_html
from loopora.specs import SpecError, compile_markdown_spec
from loopora.strategy_source import (
    load_strategy_source_file,
    normalize_strategy_role_display_name,
    normalize_strategy_source,
)

from loopora.cli_common import get_service


def spec_validation_from_markdown(markdown_text: str) -> dict[str, object]:
    try:
        compiled = compile_markdown_spec(markdown_text)
    except SpecError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "check_count": 0,
            "check_mode": "",
        }
    return {
        "ok": True,
        "error": "",
        "check_count": len(compiled["checks"]),
        "check_mode": compiled["check_mode"],
    }


def spec_document_payload(path: Path, markdown_text: str) -> dict[str, object]:
    return {
        "ok": True,
        "path": str(path.resolve()),
        "content": markdown_text,
        "rendered_html": render_safe_markdown_html(markdown_text),
        "validation": spec_validation_from_markdown(markdown_text),
    }


def resolve_spec_template_strategy_source(
    *,
    orchestration_id: str,
    strategy_preset: str,
    strategy_file: Path | None,
) -> dict | None:
    if strategy_file is not None:
        strategy_source, _ = load_strategy_source_file(strategy_file)
        return normalize_strategy_source(strategy_source) if strategy_source else None
    if orchestration_id.strip():
        orchestration = get_service().get_orchestration(orchestration_id.strip())
        strategy_source = orchestration.get("workflow_json") or None
        return normalize_strategy_source(strategy_source) if strategy_source else None
    if strategy_preset.strip():
        return normalize_strategy_source({"preset": strategy_preset.strip()})
    return None


def role_note_sections_for_strategy_source(strategy_source: dict | None) -> list[dict[str, str]]:
    if not strategy_source:
        return []
    sections: list[dict[str, str]] = []
    seen: set[str] = set()
    for role in strategy_source.get("roles", []):
        if not isinstance(role, dict):
            continue
        label = normalize_strategy_role_display_name(role.get("name"), archetype=role.get("archetype")) or str(
            role.get("name", "")
        ).strip()
        normalized = label.lower()
        if not label or normalized in seen:
            continue
        seen.add(normalized)
        sections.append({"heading": f"{label} Notes", "role_name": label})
    return sections
