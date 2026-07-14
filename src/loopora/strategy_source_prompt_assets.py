from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from loopora.strategy_source_constants import (
    LEGACY_ROLE_TO_ARCHETYPE,
    PROMPT_ASSET_DIR,
    PROMPT_FILES,
    SPEC_PRACTICE_ASSET_DIR,
)
from loopora.strategy_source_errors import WorkflowError

PROMPT_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def normalize_prompt_locale(value: str | None) -> str:
    return "zh" if str(value or "").strip().lower().startswith("zh") else "en"


def normalize_prompt_ref(value: str | None) -> str:
    prompt_ref = str(value or "").strip()
    if not prompt_ref:
        raise WorkflowError("prompt_ref is required")
    normalized = prompt_ref.replace("\\", "/")
    parts = normalized.split("/")
    if normalized.startswith("/") or any(not part or part in {".", ".."} for part in parts):
        raise WorkflowError("prompt_ref must be a safe relative path")
    return PurePosixPath(*parts).as_posix()


def prompt_asset_path(root: Path, prompt_ref: str) -> Path:
    normalized_prompt_ref = normalize_prompt_ref(prompt_ref)
    return root.joinpath(*PurePosixPath(normalized_prompt_ref).parts)


def localized_prompt_ref(prompt_ref: str, locale: str | None = None) -> str:
    normalized_prompt_ref = normalize_prompt_ref(prompt_ref)
    normalized_locale = normalize_prompt_locale(locale)
    if normalized_locale != "zh":
        return normalized_prompt_ref
    path = PurePosixPath(normalized_prompt_ref)
    localized_prompt_ref = path.with_name(f"{path.stem}.zh{path.suffix}").as_posix()
    localized_path = prompt_asset_path(PROMPT_ASSET_DIR, localized_prompt_ref)
    return localized_prompt_ref if localized_path.exists() else normalized_prompt_ref


def parse_prompt_markdown(markdown_text: str) -> tuple[dict[str, Any], str]:
    text = str(markdown_text or "").strip()
    if not text:
        raise WorkflowError("prompt markdown must not be empty")
    match = PROMPT_FRONT_MATTER_RE.match(text)
    if not match:
        raise WorkflowError("prompt markdown must start with YAML front matter")
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise WorkflowError(f"invalid prompt front matter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise WorkflowError("prompt front matter must decode to a mapping")
    body = match.group(2).strip()
    if not body:
        raise WorkflowError("prompt markdown body must not be empty")
    return metadata, body


def validate_prompt_markdown(markdown_text: str, *, expected_archetype: str | None = None) -> tuple[dict[str, Any], str]:
    metadata, body = parse_prompt_markdown(markdown_text)
    version = metadata.get("version")
    if version != 1:
        raise WorkflowError("prompt front matter requires version: 1")
    if "archetype" not in metadata:
        raise WorkflowError("prompt front matter requires archetype")
    archetype = _normalize_prompt_archetype(str(metadata.get("archetype", "")))
    if expected_archetype and archetype != _normalize_prompt_archetype(expected_archetype):
        raise WorkflowError(f"prompt archetype {archetype} does not match expected archetype {expected_archetype}")
    metadata["archetype"] = archetype
    return metadata, body


def builtin_strategy_prompt_markdown(prompt_ref: str, *, locale: str | None = None) -> str:
    path = prompt_asset_path(PROMPT_ASSET_DIR, localized_prompt_ref(prompt_ref, locale))
    if not path.exists():
        raise WorkflowError(f"unknown built-in prompt template: {prompt_ref}")
    return path.read_text(encoding="utf-8")


def builtin_prompt_markdown(prompt_ref: str, *, locale: str | None = None) -> str:
    return builtin_strategy_prompt_markdown(prompt_ref, locale=locale)


def resolve_strategy_prompt_file_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise WorkflowError("prompt file could not be read") from exc


def load_strategy_prompt_file(path: Path) -> str:
    resolved_path = resolve_strategy_prompt_file_path(path)
    try:
        return resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkflowError("prompt file must be UTF-8 encoded Markdown") from exc
    except FileNotFoundError as exc:
        raise WorkflowError("prompt file does not exist") from exc
    except OSError as exc:
        raise WorkflowError("prompt file could not be read") from exc


def load_prompt_file(path: Path) -> str:
    return load_strategy_prompt_file(path)


def builtin_strategy_prompt_markdown_by_locale(prompt_ref: str) -> dict[str, str]:
    return {
        "en": builtin_strategy_prompt_markdown(prompt_ref, locale="en"),
        "zh": builtin_strategy_prompt_markdown(prompt_ref, locale="zh"),
    }


def builtin_prompt_markdown_by_locale(prompt_ref: str) -> dict[str, str]:
    return builtin_strategy_prompt_markdown_by_locale(prompt_ref)


def builtin_spec_practice(name: str, *, locale: str | None = None, known_preset_names: set[str] | None = None) -> dict[str, str]:
    preset_name = str(name or "").strip()
    if known_preset_names is not None and preset_name not in known_preset_names:
        raise WorkflowError(f"unknown workflow preset: {name}")
    normalized_locale = normalize_prompt_locale(locale)
    localized_path = SPEC_PRACTICE_ASSET_DIR / f"{preset_name}.zh.md"
    default_path = SPEC_PRACTICE_ASSET_DIR / f"{preset_name}.md"
    path = localized_path if normalized_locale == "zh" and localized_path.exists() else default_path
    if not path.exists():
        raise WorkflowError(f"missing built-in spec practice: {preset_name}")
    markdown_text = path.read_text(encoding="utf-8").strip()
    match = PROMPT_FRONT_MATTER_RE.match(markdown_text)
    if not match:
        raise WorkflowError(f"invalid built-in spec practice: {preset_name}")
    try:
        metadata = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise WorkflowError(f"invalid built-in spec practice front matter: {preset_name}") from exc
    if not isinstance(metadata, dict):
        raise WorkflowError(f"built-in spec practice front matter must decode to a mapping: {preset_name}")
    summary = str(metadata.get("summary", "")).strip()
    practice_markdown = match.group(2).strip()
    if not summary or not practice_markdown:
        raise WorkflowError(f"built-in spec practice requires summary and markdown body: {preset_name}")
    return {"summary": summary, "markdown": practice_markdown}


def available_strategy_prompt_templates() -> list[dict[str, str]]:
    templates = []
    for prompt_ref in sorted(PROMPT_FILES.values()):
        metadata, _ = validate_prompt_markdown(builtin_strategy_prompt_markdown(prompt_ref))
        templates.append(
            {
                "prompt_ref": prompt_ref,
                "archetype": metadata["archetype"],
            }
        )
    return templates


def available_prompt_templates() -> list[dict[str, str]]:
    return available_strategy_prompt_templates()


def builtin_prompt_files_for_strategy_source(strategy_source: dict) -> dict[str, str]:
    prompt_files: dict[str, str] = {}
    for role in strategy_source.get("roles", []):
        prompt_ref = str(role.get("prompt_ref", "")).strip()
        if prompt_ref and prompt_ref not in prompt_files:
            prompt_files[prompt_ref] = builtin_strategy_prompt_markdown(prompt_ref)
    return prompt_files


def builtin_prompt_files_for_workflow(workflow: dict) -> dict[str, str]:
    return builtin_prompt_files_for_strategy_source(workflow)


def _normalize_prompt_archetype(value: str | None) -> str:
    key = str(value or "").strip().lower()
    archetype = LEGACY_ROLE_TO_ARCHETYPE.get(key)
    if not archetype:
        raise WorkflowError(f"unsupported workflow archetype: {value}")
    return archetype
