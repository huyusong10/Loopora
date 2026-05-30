from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.strategy_source_definitions import (
    DEFAULT_WORKFLOW_PRESET,
    ARCHETYPES,
    LEGACY_ROLE_BY_ARCHETYPE,
    ROLE_EXECUTION_FIELDS,
    ROLE_POSTURE_FIELDS,
    WorkflowError,
    available_prompt_templates,
    build_preset_workflow,
    builtin_prompt_markdown,
    builtin_prompt_markdown_by_locale,
    default_role_execution_settings,
    default_step_action_policy,
    default_step_execution_settings,
    display_name_for_archetype,
    has_finish_gatekeeper_step,
    load_prompt_file,
    load_workflow_file,
    normalize_archetype,
    normalize_prompt_locale,
    normalize_prompt_ref,
    normalize_role_execution_settings,
    normalize_role_display_name,
    normalize_role_models,
    normalize_step_action_policy,
    normalize_step_evidence_limit,
    normalize_step_inherit_session,
    normalize_step_inputs,
    normalize_step_on_pass,
    normalize_step_parallel_group,
    normalize_workflow,
    normalize_workflow_controls,
    normalize_workflow_identifier,
    normalize_workflow_version,
    preset_names,
    prompt_asset_path,
    PROMPT_FILES,
    resolve_prompt_files,
    role_uses_execution_snapshot,
    validate_prompt_markdown,
    validate_workflow_parallel_groups,
    workflow_preset_copy,
    workflow_warnings,
)

StrategySourceError = WorkflowError
DEFAULT_STRATEGY_SOURCE_PRESET = DEFAULT_WORKFLOW_PRESET
STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES
LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE
STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS
STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS
STRATEGY_PROMPT_FILES = PROMPT_FILES


def normalize_strategy_source(
    strategy_source: dict[str, Any] | None,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    return normalize_workflow(strategy_source, role_models=role_models)


def normalize_strategy_source_identifier(value: object, *, field_name: str) -> str:
    return normalize_workflow_identifier(value, field_name=field_name)


def normalize_strategy_source_version(value: Any, *, field_name: str = "strategy source version") -> int:
    return normalize_workflow_version(value, field_name=field_name)


def build_preset_strategy_source(
    name: str = DEFAULT_STRATEGY_SOURCE_PRESET,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    return build_preset_workflow(name, role_models=role_models)


def strategy_source_preset_names(*, include_hidden: bool = False) -> list[str]:
    return preset_names(include_hidden=include_hidden)


def strategy_source_preset_copy(name: str) -> dict[str, str]:
    return workflow_preset_copy(name)


def available_strategy_prompt_templates() -> list[dict[str, str]]:
    return available_prompt_templates()


def normalize_strategy_archetype(value: str | None) -> str:
    return normalize_archetype(value)


def strategy_archetype_display_name(archetype: str, locale: str = "en") -> str:
    return display_name_for_archetype(archetype, locale=locale)


def normalize_strategy_role_display_name(name: str | None, archetype: str | None = None) -> str:
    return normalize_role_display_name(name, archetype=archetype)


def normalize_strategy_role_models(role_models: dict | None) -> dict[str, str]:
    return normalize_role_models(role_models)


def default_strategy_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    return default_role_execution_settings(executor_kind)


def normalize_strategy_role_execution_settings(
    raw_settings: Mapping[str, Any] | None = None,
    *,
    default_executor_kind: str = "codex",
) -> dict[str, str]:
    return normalize_role_execution_settings(raw_settings, default_executor_kind=default_executor_kind)


def strategy_source_has_finish_gatekeeper_step(strategy_source: dict[str, Any] | None) -> bool:
    return has_finish_gatekeeper_step(strategy_source)


def strategy_source_warnings(strategy_source: dict) -> list[str]:
    return workflow_warnings(strategy_source)


def normalize_strategy_step_evidence_limit(value: Any) -> int | None:
    return normalize_step_evidence_limit(value)


def default_strategy_step_execution_settings(*, archetype: str | None = None) -> dict[str, Any]:
    return default_step_execution_settings(archetype=archetype)


def normalize_strategy_step_on_pass(
    value: Any,
    *,
    archetype: str | None = None,
    default: str = "",
) -> str:
    return normalize_step_on_pass(value, archetype=archetype, default=default)


def normalize_strategy_step_inherit_session(value: Any, *, archetype: str | None = None) -> bool:
    return normalize_step_inherit_session(value, archetype=archetype)


def normalize_strategy_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "",
) -> dict[str, Any]:
    return normalize_step_action_policy(value, archetype=archetype, on_pass=on_pass)


def default_strategy_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    return default_step_action_policy(archetype=archetype, on_pass=on_pass)


def normalize_strategy_step_parallel_group(value: Any) -> str:
    return normalize_step_parallel_group(value)


def normalize_strategy_step_inputs(value: Any) -> dict[str, Any]:
    return normalize_step_inputs(value)


def normalize_strategy_source_controls(
    value: Any,
    *,
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return normalize_workflow_controls(value, role_by_id=role_by_id)


def validate_strategy_source_parallel_groups(
    steps: list[dict[str, Any]],
    role_by_id: dict[str, dict[str, Any]],
) -> None:
    validate_workflow_parallel_groups(steps, role_by_id)


def strategy_prompt_asset_path(root: Path, prompt_ref: str) -> Path:
    return prompt_asset_path(root, prompt_ref)


def normalize_strategy_prompt_ref(value: str | None) -> str:
    return normalize_prompt_ref(value)


def normalize_strategy_prompt_locale(value: str | None) -> str:
    return normalize_prompt_locale(value)


def builtin_strategy_prompt_markdown(prompt_ref: str, *, locale: str | None = None) -> str:
    return builtin_prompt_markdown(prompt_ref, locale=locale)


def builtin_strategy_prompt_markdown_by_locale(prompt_ref: str) -> dict[str, str]:
    return builtin_prompt_markdown_by_locale(prompt_ref)


def load_strategy_prompt_file(path: Path) -> str:
    return load_prompt_file(path)


def load_strategy_source_file(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    return load_workflow_file(path)


def resolve_strategy_prompt_files(
    strategy_source: dict,
    provided_prompt_files: dict[str, str] | None = None,
) -> dict[str, str]:
    return resolve_prompt_files(strategy_source, provided_prompt_files)


def strategy_role_uses_execution_snapshot(role: Mapping[str, Any] | None) -> bool:
    return role_uses_execution_snapshot(role)


def validate_strategy_prompt_markdown(
    markdown_text: str,
    *,
    expected_archetype: str | None = None,
) -> tuple[dict[str, Any], str]:
    return validate_prompt_markdown(markdown_text, expected_archetype=expected_archetype)
