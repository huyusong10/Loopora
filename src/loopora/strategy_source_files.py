from __future__ import annotations

"""Strategy Source file loading and prompt-file resolution."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_prompt_assets import (
    builtin_strategy_prompt_markdown,
    normalize_prompt_ref,
    validate_prompt_markdown,
)


def resolve_strategy_source_file_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise WorkflowError("strategy source file could not be read") from exc


def resolve_strategy_prompt_files(
    strategy_source: dict,
    provided_prompt_files: dict[str, str] | None = None,
) -> dict[str, str]:
    provided: dict[str, str] = {}
    for prompt_ref, markdown_text in dict(provided_prompt_files or {}).items():
        candidate = str(prompt_ref).strip()
        if not candidate:
            continue
        normalized_prompt_ref = normalize_prompt_ref(candidate)
        provided[normalized_prompt_ref] = str(markdown_text or "")
    resolved: dict[str, str] = {}
    for role in strategy_source.get("roles", []):
        prompt_ref = role["prompt_ref"]
        if prompt_ref not in resolved:
            if prompt_ref in provided:
                resolved[prompt_ref] = provided[prompt_ref]
            else:
                try:
                    resolved[prompt_ref] = builtin_strategy_prompt_markdown(prompt_ref)
                except WorkflowError as exc:
                    raise WorkflowError(f"missing prompt file for role {role['id']}: {prompt_ref}") from exc
        validate_prompt_markdown(resolved[prompt_ref], expected_archetype=role["archetype"])
    return resolved


def resolve_prompt_files(
    workflow: dict,
    provided_prompt_files: dict[str, str] | None = None,
) -> dict[str, str]:
    return resolve_strategy_prompt_files(workflow, provided_prompt_files)


def load_strategy_source_file(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    resolved_path = resolve_strategy_source_file_path(path)
    try:
        raw_text = resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkflowError("workflow file must be UTF-8 encoded YAML or JSON") from exc
    except FileNotFoundError as exc:
        raise WorkflowError("strategy source file does not exist") from exc
    except OSError as exc:
        raise WorkflowError("strategy source file could not be read") from exc
    suffix = resolved_path.suffix.lower()
    try:
        payload = (yaml.safe_load(raw_text) or {}) if suffix in {".yaml", ".yml"} else json.loads(raw_text)
    except yaml.YAMLError as exc:
        raise WorkflowError(f"invalid workflow YAML: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid workflow JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise WorkflowError("workflow file must decode to an object")
    workflow = payload.get("workflow", payload)
    if not isinstance(workflow, Mapping):
        raise WorkflowError("workflow file workflow must be an object")
    prompt_files = payload.get("prompt_files", {})
    if not isinstance(prompt_files, dict):
        raise WorkflowError("workflow file prompt_files must be a mapping")
    return dict(workflow), {str(key): str(value) for key, value in prompt_files.items()}


def load_workflow_file(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    return load_strategy_source_file(path)
