from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets

TASK_SPEC_WORKFLOW_NOTES_ASSET_NAME = "task-spec-workflow-notes.json"


@dataclass(frozen=True)
class TaskSpecWorkflowNoteContext:
    task: str
    prefers_chinese: bool
    display_language: str = ""


def task_spec_workflow_note_context(
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> TaskSpecWorkflowNoteContext:
    return TaskSpecWorkflowNoteContext(
        task=task,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def append_task_spec_workflow_note_for_task(
    bundle: dict,
    predicate: Callable[[str], bool],
    note_key: str,
    context: TaskSpecWorkflowNoteContext,
) -> None:
    if not predicate(context.task):
        return
    append_task_spec_workflow_note_from_asset(
        bundle,
        note_key=note_key,
        prefers_chinese=context.prefers_chinese,
        display_language=context.display_language,
    )


def append_task_spec_workflow_note_from_asset(
    bundle: dict,
    *,
    note_key: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    markdown = str(bundle.get("spec", {}).get("markdown") or "")
    note = task_spec_workflow_note(
        note_key,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    if note["marker"] in markdown:
        return
    bundle["spec"]["markdown"] = markdown.rstrip() + note["text"]


def task_spec_workflow_note(
    note_key: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict[str, str]:
    language = _task_spec_workflow_note_language(prefers_chinese=prefers_chinese, display_language=display_language)
    notes = _task_spec_workflow_notes_asset()
    note = notes.get(str(note_key or ""))
    if not isinstance(note, dict):
        raise ValueError(f"missing task spec workflow note asset: {note_key}")
    return {
        "marker": note["marker"],
        "text": note["locales"].get(language) or note["locales"]["en"],
    }


def _task_spec_workflow_note_language(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "zh"
    if str(display_language or "").strip().lower() == "es":
        return "es"
    return "en"


@lru_cache
def _task_spec_workflow_notes_asset() -> dict[str, dict[str, Any]]:
    asset = load_alignment_guidance_assets().task_spec_workflow_notes
    if not all(isinstance(note_key, str) and isinstance(note, dict) for note_key, note in asset.items()):
        raise ValueError(f"{TASK_SPEC_WORKFLOW_NOTES_ASSET_NAME} must map note keys to note maps")
    return {note_key: _task_spec_workflow_note_asset(note_key, note) for note_key, note in asset.items()}


def _task_spec_workflow_note_asset(note_key: str, note: dict[str, Any]) -> dict[str, Any]:
    marker = note.get("marker")
    locales = note.get("locales")
    if not isinstance(marker, str) or not marker.startswith("# "):
        raise ValueError(f"{TASK_SPEC_WORKFLOW_NOTES_ASSET_NAME}.{note_key}.marker must be a heading")
    if not isinstance(locales, dict):
        raise ValueError(f"{TASK_SPEC_WORKFLOW_NOTES_ASSET_NAME}.{note_key}.locales must be a locale map")
    return {
        "marker": marker,
        "locales": _task_spec_workflow_note_locales(note_key, locales),
    }


def _task_spec_workflow_note_locales(note_key: str, locales: dict[str, Any]) -> dict[str, str]:
    required_locales = ("en", "zh", "es")
    if not all(isinstance(locales.get(locale), str) and locales[locale].strip() for locale in required_locales):
        raise ValueError(f"{TASK_SPEC_WORKFLOW_NOTES_ASSET_NAME}.{note_key}.locales must include en/zh/es notes")
    return {locale: str(locales[locale]) for locale in required_locales}
