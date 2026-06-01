from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_controls import normalize_strategy_source_controls
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_presets import DEFAULT_STRATEGY_SOURCE_PRESET, build_preset_strategy_source
from loopora.strategy_source_roles import normalize_strategy_role_models, normalize_strategy_source_roles
from loopora.strategy_source_steps import normalize_strategy_source_steps
from loopora.strategy_source_validation import normalize_strategy_source_version
from loopora.strategy_source_warnings import strategy_source_warnings


def normalize_strategy_source(
    strategy_source: dict[str, Any] | None,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    return _normalize_strategy_source(strategy_source, role_models=role_models, version_field_name="strategy source version")


def _normalize_strategy_source(
    strategy_source: dict[str, Any] | None,
    *,
    role_models: dict[str, str] | None = None,
    version_field_name: str,
) -> dict:
    if strategy_source is None:
        return normalize_preset_strategy_source(DEFAULT_STRATEGY_SOURCE_PRESET, role_models=role_models)

    raw = dict(strategy_source)
    if strategy_source_requests_preset(raw):
        return normalize_preset_strategy_source(str(raw.get("preset")), role_models=role_models)

    raw_roles, raw_steps = require_strategy_source_entries(raw)
    roles = normalize_strategy_source_roles(raw_roles, role_models=normalize_strategy_role_models(role_models))
    role_by_id = {role["id"]: role for role in roles}
    steps = normalize_strategy_source_steps(raw_steps, role_by_id=role_by_id)
    controls = normalize_strategy_source_controls(raw.get("controls"), role_by_id=role_by_id)

    normalized = {
        "version": normalize_strategy_source_version(raw.get("version"), field_name=version_field_name),
        "preset": str(raw.get("preset", "")).strip(),
        "collaboration_intent": str(raw.get("collaboration_intent", "") or "").strip(),
        "roles": roles,
        "steps": steps,
    }
    if controls:
        normalized["controls"] = controls
    normalized["warnings"] = strategy_source_warnings(normalized)
    return normalized


def normalize_workflow(workflow: dict[str, Any] | None, *, role_models: dict[str, str] | None = None) -> dict:
    return _normalize_strategy_source(workflow, role_models=role_models, version_field_name="workflow version")


def normalize_preset_strategy_source(preset: str, *, role_models: dict[str, str] | None = None) -> dict:
    normalized = build_preset_strategy_source(preset, role_models=role_models)
    normalized["warnings"] = strategy_source_warnings(normalized)
    return normalized


def normalize_preset_workflow(preset: str, *, role_models: dict[str, str] | None = None) -> dict:
    return normalize_preset_strategy_source(preset, role_models=role_models)


def strategy_source_requests_preset(raw: Mapping[str, Any]) -> bool:
    return bool(raw.get("preset") and not raw.get("roles") and not raw.get("steps"))


def workflow_requests_preset(raw: Mapping[str, Any]) -> bool:
    return strategy_source_requests_preset(raw)


def require_strategy_source_entries(raw: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    raw_roles = raw.get("roles")
    raw_steps = raw.get("steps")
    if not isinstance(raw_roles, list) or not raw_roles:
        raise WorkflowError("workflow requires at least one role")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise WorkflowError("workflow requires at least one step")
    return raw_roles, raw_steps


def require_workflow_entries(raw: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    return require_strategy_source_entries(raw)
