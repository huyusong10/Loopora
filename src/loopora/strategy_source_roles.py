from __future__ import annotations

from collections.abc import Mapping

from typing import Any

from loopora.executor_command_args import validate_command_args_text

from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode, normalize_reasoning_setting

from loopora.strategy_source_constants import ROLE_EXECUTION_FIELDS

def default_strategy_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    profile = executor_profile(executor_kind)
    default_mode = "command" if profile.command_only else "preset"
    return {
        "executor_kind": profile.key,
        "executor_mode": default_mode,
        "command_cli": profile.cli_name,
        "command_args_text": "\n".join(profile.command_args_template) if default_mode == "command" else "",
        "model": profile.default_model,
        "reasoning_effort": profile.effort_default,
    }

def default_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    return default_strategy_role_execution_settings(executor_kind)

def normalize_strategy_role_execution_settings(
    raw_settings: Mapping[str, Any] | None = None,
    *,
    default_executor_kind: str = "codex",
) -> dict[str, str]:
    settings = dict(raw_settings or {})
    executor_kind = normalize_executor_kind(str(settings.get("executor_kind", default_executor_kind)).strip() or default_executor_kind)
    executor_mode = normalize_executor_mode(str(settings.get("executor_mode", "preset")).strip() or "preset")
    profile = executor_profile(executor_kind)
    model = str(settings.get("model", "")).strip()
    reasoning_effort = str(settings.get("reasoning_effort", "")).strip()
    command_cli = str(settings.get("command_cli", "")).strip()
    command_args_text = str(settings.get("command_args_text", ""))

    if profile.command_only and executor_mode != "command":
        raise ValueError(f"{profile.label} only supports command mode")

    if executor_mode == "preset":
        command_cli = profile.cli_name
        command_args_text = ""
        reasoning_effort = normalize_reasoning_setting(reasoning_effort, executor_kind=executor_kind)
        if not model and profile.default_model:
            model = profile.default_model
    else:
        command_cli = command_cli or profile.cli_name
        validate_command_args_text(command_args_text, executor_kind=executor_kind)

    return {
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "command_cli": command_cli,
        "command_args_text": command_args_text,
        "model": model,
        "reasoning_effort": reasoning_effort,
    }

def normalize_role_execution_settings(
    raw_settings: Mapping[str, Any] | None = None,
    *,
    default_executor_kind: str = "codex",
) -> dict[str, str]:
    return normalize_strategy_role_execution_settings(raw_settings, default_executor_kind=default_executor_kind)

def strategy_role_uses_execution_snapshot(role: Mapping[str, Any] | None) -> bool:
    if not isinstance(role, Mapping):
        return False
    return any(key in role for key in ROLE_EXECUTION_FIELDS)

def role_uses_execution_snapshot(role: Mapping[str, Any] | None) -> bool:
    return strategy_role_uses_execution_snapshot(role)

"""Strategy Source role and archetype normalization rules."""


from loopora.strategy_source_constants import (
    ARCHETYPE_DISPLAY,
    ARCHETYPE_DISPLAY_ALIASES,
    ARCHETYPES,
    LEGACY_ROLE_TO_ARCHETYPE,
    PROMPT_FILES,
)
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_prompt_assets import normalize_prompt_ref
from loopora.strategy_source_validation import normalize_optional_strategy_source_identifier


def normalize_strategy_archetype(value: str | None) -> str:
    key = str(value or "").strip().lower()
    archetype = LEGACY_ROLE_TO_ARCHETYPE.get(key)
    if not archetype:
        raise WorkflowError(f"unsupported workflow archetype: {value}")
    return archetype


def normalize_archetype(value: str | None) -> str:
    return normalize_strategy_archetype(value)


def normalize_strategy_role_models(role_models: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if not role_models:
        return normalized
    for raw_role, raw_model in dict(role_models).items():
        role_key = str(raw_role).strip()
        model = str(raw_model).strip()
        if not role_key:
            raise WorkflowError("role model overrides require a role name")
        if not model:
            raise WorkflowError(f"invalid role model override: {raw_role}={raw_model}")
        archetype = LEGACY_ROLE_TO_ARCHETYPE.get(role_key.lower())
        if archetype:
            normalized[archetype] = model
            continue
        normalized[role_key] = model
    return normalized


def normalize_role_models(role_models: dict[str, str] | None) -> dict[str, str]:
    return normalize_strategy_role_models(role_models)


def strategy_archetype_display_name(archetype: str, locale: str = "en") -> str:
    labels = ARCHETYPE_DISPLAY[normalize_strategy_archetype(archetype)]
    return labels["zh" if locale.lower().startswith("zh") else "en"]


def display_name_for_archetype(archetype: str, locale: str = "en") -> str:
    return strategy_archetype_display_name(archetype, locale=locale)


def normalize_strategy_role_display_name(name: str | None, archetype: str | None = None) -> str:
    raw_name = str(name or "").strip()
    if not raw_name:
        return ""
    if archetype:
        normalized_archetype = normalize_strategy_archetype(archetype)
        canonical = strategy_archetype_display_name(normalized_archetype, locale="en")
        aliases = {alias.lower() for alias in ARCHETYPE_DISPLAY_ALIASES.get(normalized_archetype, set())}
        lowered = raw_name.lower()
        if lowered == canonical.lower() or lowered in aliases:
            return canonical
        return raw_name
    lowered = raw_name.lower()
    for candidate in ARCHETYPES:
        canonical = strategy_archetype_display_name(candidate, locale="en")
        aliases = {alias.lower() for alias in ARCHETYPE_DISPLAY_ALIASES.get(candidate, set())}
        if lowered == canonical.lower() or lowered in aliases:
            return canonical
    return raw_name


def normalize_role_display_name(name: str | None, archetype: str | None = None) -> str:
    return normalize_strategy_role_display_name(name, archetype=archetype)


def normalize_strategy_source_roles(
    raw_roles: list[Any],
    *,
    role_models: Mapping[str, str],
) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    role_ids: set[str] = set()
    for index, raw_role in enumerate(raw_roles, start=1):
        roles.append(normalize_strategy_source_role(raw_role, index=index, role_ids=role_ids, role_models=role_models))
    return roles


def normalize_workflow_roles(
    raw_roles: list[Any],
    *,
    role_models: Mapping[str, str],
) -> list[dict[str, Any]]:
    return normalize_strategy_source_roles(raw_roles, role_models=role_models)


def normalize_strategy_source_role(
    raw_role: Any,
    *,
    index: int,
    role_ids: set[str],
    role_models: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(raw_role, dict):
        raise WorkflowError("workflow roles must be objects")
    role_id = normalize_optional_strategy_source_identifier(
        raw_role.get("id"),
        default=f"role_{index:03d}",
        field_name="workflow role id",
    )
    if role_id in role_ids:
        raise WorkflowError(f"duplicate workflow role id: {role_id}")
    archetype = normalize_strategy_archetype(str(raw_role.get("archetype", "")))
    prompt_ref = normalize_prompt_ref(raw_role.get("prompt_ref") or PROMPT_FILES[archetype])
    raw_name = str(raw_role.get("name", "")).strip()
    name = normalize_strategy_role_display_name(raw_name, archetype) or strategy_archetype_display_name(
        archetype,
        locale="en",
    )
    model = str(raw_role.get("model", "")).strip()
    role_definition_id = str(raw_role.get("role_definition_id", "")).strip()
    override_model = role_models.get(role_id, role_models.get(archetype, ""))
    if override_model:
        model = override_model
    role_ids.add(role_id)
    role_entry = {
        "id": role_id,
        "name": name,
        "archetype": archetype,
        "prompt_ref": prompt_ref,
        "model": model,
        "role_definition_id": role_definition_id,
        "posture_notes": str(raw_role.get("posture_notes", "") or "").strip(),
    }
    if strategy_role_uses_execution_snapshot(raw_role):
        execution_settings = normalize_strategy_role_execution_settings(raw_role)
        role_entry.update(execution_settings)
        if model:
            role_entry["model"] = model
    return role_entry


def normalize_workflow_role(
    raw_role: Any,
    *,
    index: int,
    role_ids: set[str],
    role_models: Mapping[str, str],
) -> dict[str, Any]:
    return normalize_strategy_source_role(raw_role, index=index, role_ids=role_ids, role_models=role_models)
