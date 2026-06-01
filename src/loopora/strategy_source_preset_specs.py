from __future__ import annotations

"""Typed preset specs and builder helpers for Strategy Source presets."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from loopora.strategy_source_constants import ARCHETYPE_DISPLAY
from loopora.strategy_source_execution_settings import default_strategy_role_execution_settings
from loopora.strategy_source_steps import (
    default_strategy_step_execution_settings,
    normalize_strategy_step_action_policy,
    normalize_strategy_step_inherit_session,
    normalize_strategy_step_inputs,
    normalize_strategy_step_on_pass,
    normalize_strategy_step_parallel_group,
)


@dataclass(frozen=True, kw_only=True)
class PresetRoleSpec:
    role_id: str
    archetype: str
    prompt_ref: str
    role_definition_id: str
    name: str = ""
    posture_notes: str = ""


@dataclass(frozen=True, kw_only=True)
class StrategySourcePresetDefinitionSpec:
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str
    scenario_zh: str
    scenario_en: str
    roles: list[dict[str, str]]
    steps: list[dict[str, Any]]
    choice_zh: str = ""
    choice_en: str = ""
    decision_zh: str = ""
    decision_en: str = ""
    visible: bool = True


WorkflowPresetDefinitionSpec = StrategySourcePresetDefinitionSpec


@dataclass(frozen=True, kw_only=True)
class PresetStepSpec:
    step_id: str
    role_id: str
    archetype: str
    on_pass: str | None = None
    model: str = ""
    inherit_session: bool | None = None
    extra_cli_args: str = ""
    parallel_group: str = ""
    inputs: dict[str, Any] | None = None
    action_policy: dict[str, Any] | None = None


def preset_role(spec: PresetRoleSpec | None = None, **raw_spec: Any) -> dict[str, str]:
    role_spec = _coerce_preset_role_spec(spec, raw_spec)
    return {
        "id": role_spec.role_id,
        "name": role_spec.name or ARCHETYPE_DISPLAY[role_spec.archetype]["en"],
        "archetype": role_spec.archetype,
        "prompt_ref": role_spec.prompt_ref,
        "role_definition_id": role_spec.role_definition_id,
        "posture_notes": role_spec.posture_notes,
        **default_strategy_role_execution_settings(),
    }


def _coerce_preset_role_spec(spec: PresetRoleSpec | None, raw_spec: Mapping[str, Any]) -> PresetRoleSpec:
    if spec is not None and raw_spec:
        raise TypeError("preset role spec cannot mix object and keyword fields")
    return spec or PresetRoleSpec(**raw_spec)


def strategy_source_preset_definition(
    spec: StrategySourcePresetDefinitionSpec | None = None,
    **raw_spec: Any,
) -> dict[str, Any]:
    preset_spec = _coerce_strategy_source_preset_definition_spec(spec, raw_spec)
    return {
        "label_zh": preset_spec.label_zh,
        "label_en": preset_spec.label_en,
        "description_zh": preset_spec.description_zh,
        "description_en": preset_spec.description_en,
        "scenario_zh": preset_spec.scenario_zh,
        "scenario_en": preset_spec.scenario_en,
        "choice_zh": preset_spec.choice_zh,
        "choice_en": preset_spec.choice_en,
        "decision_zh": preset_spec.decision_zh,
        "decision_en": preset_spec.decision_en,
        "visible": preset_spec.visible,
        "workflow": {
            "collaboration_intent": preset_spec.decision_en,
            "roles": preset_spec.roles,
            "steps": preset_spec.steps,
        },
    }


def _coerce_strategy_source_preset_definition_spec(
    spec: StrategySourcePresetDefinitionSpec | None,
    raw_spec: Mapping[str, Any],
) -> StrategySourcePresetDefinitionSpec:
    if spec is not None and raw_spec:
        raise TypeError("strategy source preset spec cannot mix object and keyword fields")
    return spec or StrategySourcePresetDefinitionSpec(**raw_spec)


workflow_preset_definition = strategy_source_preset_definition


def preset_step(spec: PresetStepSpec | None = None, **raw_spec: Any) -> dict[str, Any]:
    step_spec = _coerce_preset_step_spec(spec, raw_spec)
    defaults = default_strategy_step_execution_settings(archetype=step_spec.archetype)
    normalized_on_pass = normalize_strategy_step_on_pass(
        step_spec.on_pass,
        archetype=step_spec.archetype,
        default=defaults["on_pass"],
    )
    step = {
        "id": step_spec.step_id,
        "role_id": step_spec.role_id,
        "on_pass": normalized_on_pass,
        "model": step_spec.model,
        "inherit_session": normalize_strategy_step_inherit_session(
            step_spec.inherit_session,
            archetype=step_spec.archetype,
        ),
        "extra_cli_args": str(step_spec.extra_cli_args or ""),
        "action_policy": normalize_strategy_step_action_policy(
            step_spec.action_policy,
            archetype=step_spec.archetype,
            on_pass=normalized_on_pass,
        ),
    }
    normalized_parallel_group = normalize_strategy_step_parallel_group(step_spec.parallel_group)
    if normalized_parallel_group:
        step["parallel_group"] = normalized_parallel_group
    normalized_inputs = normalize_strategy_step_inputs(step_spec.inputs)
    if normalized_inputs:
        step["inputs"] = normalized_inputs
    return step


def _coerce_preset_step_spec(spec: PresetStepSpec | None, raw_spec: Mapping[str, Any]) -> PresetStepSpec:
    if spec is not None and raw_spec:
        raise TypeError("preset step spec cannot mix object and keyword fields")
    return spec or PresetStepSpec(**raw_spec)
