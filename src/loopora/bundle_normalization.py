from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_contract import (
    BUNDLE_VERSION,
    BundleError,
    normalize_bundle_identifier,
    normalize_bundle_integer,
)
from loopora.bundle_loop_settings import bundle_loop_role_execution_defaults, normalize_bundle_loop
from loopora.bundle_workflow_normalization import normalize_bundle_workflow, validate_bundle_runtime_contract
from loopora.specs import SpecError, compile_markdown_spec

import re



from loopora.bundle_contract import BUNDLE_EXECUTION_FIELDS

from loopora.providers import normalize_executor_kind

from loopora.strategy_source import (
    StrategySourceError,
    normalize_strategy_archetype,
    normalize_strategy_prompt_ref,
    normalize_strategy_role_execution_settings,
    validate_strategy_prompt_markdown,
)

ROLE_DEFINITION_KEY_RE = re.compile(r"[^a-z0-9]+")

def _slugify_bundle_role_key(value: str) -> str:
    normalized = ROLE_DEFINITION_KEY_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return normalized or "role"

def normalize_bundle_role_definitions(raw_role_definitions: object, *, default_execution: Mapping[str, str]) -> list[dict[str, Any]]:
    if not isinstance(raw_role_definitions, list) or not raw_role_definitions:
        raise BundleError("bundle role_definitions must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for index, raw_entry in enumerate(raw_role_definitions, start=1):
        normalized.append(
            _normalize_bundle_role_definition(
                raw_entry,
                index=index,
                seen_keys=seen_keys,
                default_execution=default_execution,
            )
        )
    return normalized

def _normalize_bundle_role_definition(
    raw_entry: object,
    *,
    index: int,
    seen_keys: set[str],
    default_execution: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(raw_entry, Mapping):
        raise BundleError("bundle role_definitions entries must be objects")
    entry = dict(raw_entry)
    key = _normalize_bundle_role_definition_key(entry, index=index, seen_keys=seen_keys)
    name = _require_bundle_role_definition_text(entry, key=key, field_name="name")
    archetype = _require_bundle_role_definition_text(entry, key=key, field_name="archetype")
    prompt_markdown = _require_bundle_role_definition_text(entry, key=key, field_name="prompt_markdown", strip=False)
    try:
        normalized_archetype = _normalize_bundle_role_archetype(archetype, prompt_markdown=prompt_markdown)
        execution = _normalize_bundle_role_execution(entry, default_execution=default_execution)
    except (StrategySourceError, ValueError) as exc:
        raise BundleError(str(exc)) from exc
    return {
        "key": key,
        "name": name,
        "description": str(entry.get("description", "") or "").strip(),
        "archetype": normalized_archetype,
        "prompt_ref": _normalize_bundle_role_prompt_ref(entry.get("prompt_ref"), key=key),
        "prompt_markdown": prompt_markdown,
        "posture_notes": str(entry.get("posture_notes", "") or "").strip(),
        **execution,
    }

def _normalize_bundle_role_definition_key(
    entry: Mapping[str, Any],
    *,
    index: int,
    seen_keys: set[str],
) -> str:
    raw_key = str(entry.get("key", "") or entry.get("id", "") or entry.get("name", "") or f"role-{index}")
    key = _slugify_bundle_role_key(raw_key)
    if key in seen_keys:
        raise BundleError(f"duplicate bundle role_definition key: {key}")
    seen_keys.add(key)
    return key

def _require_bundle_role_definition_text(
    entry: Mapping[str, Any],
    *,
    key: str,
    field_name: str,
    strip: bool = True,
) -> str:
    value = str(entry.get(field_name, "") or "")
    normalized = value.strip() if strip else value
    if not normalized.strip():
        raise BundleError(f"bundle role_definition {key} requires {field_name}")
    return normalized

def _normalize_bundle_role_prompt_ref(value: object, *, key: str) -> str:
    prompt_ref = str(value or "").strip()
    if not prompt_ref:
        return f"{key}.md"
    try:
        return normalize_strategy_prompt_ref(prompt_ref)
    except StrategySourceError as exc:
        raise BundleError(str(exc)) from exc

def _normalize_bundle_role_archetype(archetype: str, *, prompt_markdown: str) -> str:
    normalized_archetype = normalize_strategy_archetype(archetype)
    validate_strategy_prompt_markdown(prompt_markdown, expected_archetype=normalized_archetype)
    return normalized_archetype

def _normalize_bundle_role_execution(entry: Mapping[str, Any], *, default_execution: Mapping[str, str]) -> dict[str, str]:
    if not any(field in entry for field in BUNDLE_EXECUTION_FIELDS):
        return dict(default_execution)
    try:
        executor_kind_changed = (
            "executor_kind" in entry
            and normalize_executor_kind(str(entry.get("executor_kind") or "").strip()) != str(default_execution.get("executor_kind") or "codex")
        )
    except ValueError as exc:
        raise BundleError(str(exc)) from exc
    if executor_kind_changed:
        settings = {
            "executor_kind": entry.get("executor_kind"),
            "executor_mode": entry.get("executor_mode", "preset"),
            "command_cli": entry.get("command_cli", ""),
            "command_args_text": entry.get("command_args_text", ""),
            "model": entry.get("model", ""),
            "reasoning_effort": entry.get("reasoning_effort", ""),
        }
    else:
        settings = {field: default_execution.get(field, "") for field in BUNDLE_EXECUTION_FIELDS}
        for field in BUNDLE_EXECUTION_FIELDS:
            if field in entry:
                settings[field] = entry.get(field)
    return normalize_strategy_role_execution_settings(
        settings,
        default_executor_kind=str(default_execution.get("executor_kind") or "codex"),
    )


def normalize_bundle(payload: Mapping[str, object] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise BundleError("bundle payload must decode to an object")
    raw = dict(payload)
    version = _normalize_bundle_version(raw.get("version"))
    if version != BUNDLE_VERSION:
        raise BundleError(f"unsupported bundle version: {version}")

    metadata = _normalize_bundle_metadata(raw.get("metadata"))
    collaboration_summary = str(raw.get("collaboration_summary", "") or "").strip()
    if not collaboration_summary:
        raise BundleError("bundle collaboration_summary is required")
    loop = normalize_bundle_loop(raw.get("loop"))
    spec = _normalize_bundle_spec(raw.get("spec"))
    role_definitions = normalize_bundle_role_definitions(
        raw.get("role_definitions"),
        default_execution=bundle_loop_role_execution_defaults(loop),
    )
    workflow = normalize_bundle_workflow(raw.get("workflow"), role_definitions=role_definitions)
    validate_bundle_runtime_contract(loop=loop, role_definitions=role_definitions, workflow=workflow)
    return {
        "version": version,
        "metadata": metadata,
        "collaboration_summary": collaboration_summary,
        "loop": loop,
        "spec": spec,
        "role_definitions": role_definitions,
        "workflow": workflow,
    }


def _normalize_bundle_metadata(raw_metadata: object) -> dict[str, Any]:
    if raw_metadata is None:
        metadata = {}
    elif isinstance(raw_metadata, Mapping):
        metadata = dict(raw_metadata)
    else:
        raise BundleError("bundle metadata must be an object")
    name = str(metadata.get("name", "") or "").strip()
    if not name:
        raise BundleError("bundle metadata.name is required")
    revision = _normalize_bundle_revision(metadata)
    if revision < 1:
        raise BundleError("bundle metadata.revision must be >= 1")
    return {
        "bundle_id": normalize_bundle_identifier(metadata.get("bundle_id"), field_name="bundle metadata.bundle_id", allow_empty=True),
        "name": name,
        "description": str(metadata.get("description", "") or "").strip(),
        "source_bundle_id": normalize_bundle_identifier(
            metadata.get("source_bundle_id"),
            field_name="bundle metadata.source_bundle_id",
            allow_empty=True,
        ),
        "revision": revision,
    }


def _normalize_bundle_version(value: object) -> int:
    return normalize_bundle_integer(value, default=BUNDLE_VERSION, field_name="bundle version")


def _normalize_bundle_revision(metadata: Mapping[str, Any]) -> int:
    if "revision" not in metadata:
        return 1
    value = metadata.get("revision")
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BundleError("bundle metadata.revision must be an integer")
    return normalize_bundle_integer(value, default=1, field_name="bundle metadata.revision")


def _normalize_bundle_spec(raw_spec: object) -> dict[str, str]:
    if not isinstance(raw_spec, Mapping):
        raise BundleError("bundle spec must be an object")
    markdown = str(dict(raw_spec).get("markdown", "") or "").strip()
    if not markdown:
        raise BundleError("bundle spec.markdown is required")
    try:
        compile_markdown_spec(markdown)
    except SpecError as exc:
        raise BundleError(str(exc)) from exc
    return {"markdown": markdown}
