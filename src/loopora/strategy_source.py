from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.strategy_source_definitions import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    LEGACY_STRATEGY_ROLE_BY_ARCHETYPE as LEGACY_STRATEGY_ROLE_BY_ARCHETYPE,
    STRATEGY_PROMPT_FILES as STRATEGY_PROMPT_FILES,
    STRATEGY_ROLE_EXECUTION_FIELDS as STRATEGY_ROLE_EXECUTION_FIELDS,
    STRATEGY_ROLE_POSTURE_FIELDS as STRATEGY_ROLE_POSTURE_FIELDS,
    STRATEGY_SOURCE_ARCHETYPES as STRATEGY_SOURCE_ARCHETYPES,
    StrategySourceError as StrategySourceError,
    available_strategy_prompt_templates as definition_available_strategy_prompt_templates,
    build_preset_strategy_source as definition_build_preset_strategy_source,
    builtin_strategy_prompt_markdown as definition_builtin_strategy_prompt_markdown,
    builtin_strategy_prompt_markdown_by_locale as definition_builtin_strategy_prompt_markdown_by_locale,
    default_strategy_role_execution_settings as definition_default_strategy_role_execution_settings,
    default_strategy_step_action_policy as definition_default_strategy_step_action_policy,
    default_strategy_step_execution_settings as definition_default_strategy_step_execution_settings,
    strategy_archetype_display_name as definition_strategy_archetype_display_name,
    load_strategy_prompt_file as definition_load_strategy_prompt_file,
    load_strategy_source_file as definition_load_strategy_source_file,
    normalize_prompt_locale,
    normalize_prompt_ref,
    normalize_strategy_archetype as definition_normalize_strategy_archetype,
    normalize_strategy_role_display_name as definition_normalize_strategy_role_display_name,
    normalize_strategy_role_execution_settings as definition_normalize_strategy_role_execution_settings,
    normalize_strategy_role_models as definition_normalize_strategy_role_models,
    normalize_strategy_step_action_policy as definition_normalize_strategy_step_action_policy,
    normalize_strategy_step_evidence_limit as definition_normalize_strategy_step_evidence_limit,
    normalize_strategy_step_inherit_session as definition_normalize_strategy_step_inherit_session,
    normalize_strategy_step_inputs as definition_normalize_strategy_step_inputs,
    normalize_strategy_step_on_pass as definition_normalize_strategy_step_on_pass,
    normalize_strategy_step_parallel_group as definition_normalize_strategy_step_parallel_group,
    normalize_strategy_source_controls as definition_normalize_strategy_source_controls,
    normalize_strategy_source_identifier as definition_normalize_strategy_source_identifier,
    normalize_strategy_source as definition_normalize_strategy_source,
    normalize_strategy_source_version as definition_normalize_strategy_source_version,
    strategy_source_preset_names as definition_strategy_source_preset_names,
    prompt_asset_path,
    resolve_strategy_prompt_files as definition_resolve_strategy_prompt_files,
    strategy_source_has_finish_gatekeeper_step as definition_strategy_source_has_finish_gatekeeper_step,
    strategy_role_uses_execution_snapshot as definition_strategy_role_uses_execution_snapshot,
    strategy_source_preset_copy as definition_strategy_source_preset_copy,
    strategy_source_warnings as definition_strategy_source_warnings,
    validate_prompt_markdown,
    validate_strategy_source_parallel_groups as definition_validate_strategy_source_parallel_groups,
)


def normalize_strategy_source(
    strategy_source: dict[str, Any] | None,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    return definition_normalize_strategy_source(strategy_source, role_models=role_models)


def strategy_source_from_record(record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Read a Strategy Source from a projected record with storage compatibility."""
    if not isinstance(record, Mapping):
        return None
    strategy_source = record.get("strategy_source")
    if isinstance(strategy_source, Mapping):
        return dict(strategy_source)
    storage_source = record.get("workflow_json")
    return dict(storage_source) if isinstance(storage_source, Mapping) else None


def normalize_strategy_source_identifier(value: object, *, field_name: str) -> str:
    return definition_normalize_strategy_source_identifier(value, field_name=field_name)


def normalize_strategy_source_version(value: Any, *, field_name: str = "strategy source version") -> int:
    return definition_normalize_strategy_source_version(value, field_name=field_name)


def build_preset_strategy_source(
    name: str = DEFAULT_STRATEGY_SOURCE_PRESET,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    return definition_build_preset_strategy_source(name, role_models=role_models)


def strategy_source_preset_names(*, include_hidden: bool = False) -> list[str]:
    return definition_strategy_source_preset_names(include_hidden=include_hidden)


def strategy_source_preset_copy(name: str) -> dict[str, str]:
    return definition_strategy_source_preset_copy(name)


def available_strategy_prompt_templates() -> list[dict[str, str]]:
    return definition_available_strategy_prompt_templates()


def normalize_strategy_archetype(value: str | None) -> str:
    return definition_normalize_strategy_archetype(value)


def strategy_archetype_display_name(archetype: str, locale: str = "en") -> str:
    return definition_strategy_archetype_display_name(archetype, locale=locale)


def normalize_strategy_role_display_name(name: str | None, archetype: str | None = None) -> str:
    return definition_normalize_strategy_role_display_name(name, archetype=archetype)


def normalize_strategy_role_models(role_models: dict | None) -> dict[str, str]:
    return definition_normalize_strategy_role_models(role_models)


def default_strategy_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    return definition_default_strategy_role_execution_settings(executor_kind)


def normalize_strategy_role_execution_settings(
    raw_settings: Mapping[str, Any] | None = None,
    *,
    default_executor_kind: str = "codex",
) -> dict[str, str]:
    return definition_normalize_strategy_role_execution_settings(
        raw_settings,
        default_executor_kind=default_executor_kind,
    )


def strategy_source_has_finish_gatekeeper_step(strategy_source: dict[str, Any] | None) -> bool:
    return definition_strategy_source_has_finish_gatekeeper_step(strategy_source)


def strategy_source_warnings(strategy_source: dict) -> list[str]:
    return definition_strategy_source_warnings(strategy_source)


def normalize_strategy_step_evidence_limit(value: Any) -> int | None:
    return definition_normalize_strategy_step_evidence_limit(value)


def default_strategy_step_execution_settings(*, archetype: str | None = None) -> dict[str, Any]:
    return definition_default_strategy_step_execution_settings(archetype=archetype)


def normalize_strategy_step_on_pass(
    value: Any,
    *,
    archetype: str | None = None,
    default: str = "",
) -> str:
    return definition_normalize_strategy_step_on_pass(value, archetype=archetype, default=default)


def normalize_strategy_step_inherit_session(value: Any, *, archetype: str | None = None) -> bool:
    return definition_normalize_strategy_step_inherit_session(value, archetype=archetype)


def normalize_strategy_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "",
) -> dict[str, Any]:
    return definition_normalize_strategy_step_action_policy(value, archetype=archetype, on_pass=on_pass)


def default_strategy_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    return definition_default_strategy_step_action_policy(archetype=archetype, on_pass=on_pass)


def normalize_strategy_step_parallel_group(value: Any) -> str:
    return definition_normalize_strategy_step_parallel_group(value)


def normalize_strategy_step_inputs(value: Any) -> dict[str, Any]:
    return definition_normalize_strategy_step_inputs(value)


def normalize_strategy_source_controls(
    value: Any,
    *,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return definition_normalize_strategy_source_controls(value, role_by_id=role_by_id)


def validate_strategy_source_parallel_groups(
    steps: list[dict[str, Any]],
    role_by_id: dict[str, dict[str, Any]],
) -> None:
    definition_validate_strategy_source_parallel_groups(steps, role_by_id)


def strategy_prompt_asset_path(root: Path, prompt_ref: str) -> Path:
    return prompt_asset_path(root, prompt_ref)


def normalize_strategy_prompt_ref(value: str | None) -> str:
    return normalize_prompt_ref(value)


def normalize_strategy_prompt_locale(value: str | None) -> str:
    return normalize_prompt_locale(value)


def builtin_strategy_prompt_markdown(prompt_ref: str, *, locale: str | None = None) -> str:
    return definition_builtin_strategy_prompt_markdown(prompt_ref, locale=locale)


def builtin_strategy_prompt_markdown_by_locale(prompt_ref: str) -> dict[str, str]:
    return definition_builtin_strategy_prompt_markdown_by_locale(prompt_ref)


def load_strategy_prompt_file(path: Path) -> str:
    return definition_load_strategy_prompt_file(path)


def load_strategy_source_file(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    return definition_load_strategy_source_file(path)


def resolve_strategy_prompt_files(
    strategy_source: dict,
    provided_prompt_files: dict[str, str] | None = None,
) -> dict[str, str]:
    return definition_resolve_strategy_prompt_files(strategy_source, provided_prompt_files)


def strategy_role_uses_execution_snapshot(role: Mapping[str, Any] | None) -> bool:
    return definition_strategy_role_uses_execution_snapshot(role)


def validate_strategy_prompt_markdown(
    markdown_text: str,
    *,
    expected_archetype: str | None = None,
) -> tuple[dict[str, Any], str]:
    return validate_prompt_markdown(markdown_text, expected_archetype=expected_archetype)
