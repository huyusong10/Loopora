from __future__ import annotations

"""Strategy Source preset assembly and public preset metadata helpers."""

import json

from loopora.strategy_source_constants import PROMPT_FILES
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_preset_catalog import build_strategy_source_presets
from loopora.strategy_source_preset_specs import (
    PresetRoleSpec as PresetRoleSpec,
    PresetStepSpec as PresetStepSpec,
    StrategySourcePresetDefinitionSpec as StrategySourcePresetDefinitionSpec,
    WorkflowPresetDefinitionSpec as WorkflowPresetDefinitionSpec,
    preset_role as _preset_role,
    preset_step as _preset_step,
    strategy_source_preset_definition as _strategy_source_preset_definition,
)
from loopora.strategy_source_prompt_assets import builtin_spec_practice as _builtin_spec_practice
from loopora.strategy_source_roles import normalize_strategy_role_models


DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"
DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET


STRATEGY_SOURCE_PRESETS = build_strategy_source_presets(
    preset_definition=_strategy_source_preset_definition,
    preset_role=_preset_role,
    preset_step=_preset_step,
    prompt_files=PROMPT_FILES,
)
WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS


def builtin_spec_practice(name: str, *, locale: str | None = None) -> dict[str, str]:
    return _builtin_spec_practice(name, locale=locale, known_preset_names=set(STRATEGY_SOURCE_PRESETS))


def strategy_source_preset_names(*, include_hidden: bool = False) -> list[str]:
    names: list[str] = []
    for preset_name, preset in STRATEGY_SOURCE_PRESETS.items():
        if include_hidden or bool(preset.get("visible", True)):
            names.append(preset_name)
    return names


def preset_names(*, include_hidden: bool = False) -> list[str]:
    return strategy_source_preset_names(include_hidden=include_hidden)


def strategy_source_preset_copy(name: str) -> dict[str, str]:
    preset_name = str(name or DEFAULT_STRATEGY_SOURCE_PRESET).strip() or DEFAULT_STRATEGY_SOURCE_PRESET
    preset = STRATEGY_SOURCE_PRESETS.get(preset_name)
    if not preset:
        raise WorkflowError(f"unknown workflow preset: {name}")
    practice_en = builtin_spec_practice(preset_name, locale="en")
    practice_zh = builtin_spec_practice(preset_name, locale="zh")
    return {
        "label_zh": str(preset["label_zh"]),
        "label_en": str(preset["label_en"]),
        "description_zh": str(preset["description_zh"]),
        "description_en": str(preset["description_en"]),
        "scenario_zh": str(preset["scenario_zh"]),
        "scenario_en": str(preset["scenario_en"]),
        "choice_zh": str(preset.get("choice_zh", "")),
        "choice_en": str(preset.get("choice_en", "")),
        "decision_zh": str(preset.get("decision_zh", "")),
        "decision_en": str(preset.get("decision_en", "")),
        "visible": "true" if bool(preset.get("visible", True)) else "false",
        "spec_practice_summary_zh": practice_zh["summary"],
        "spec_practice_summary_en": practice_en["summary"],
        "spec_practice_markdown_zh": practice_zh["markdown"],
        "spec_practice_markdown_en": practice_en["markdown"],
    }


def strategy_source_preset_options(*, include_hidden: bool = False) -> list[dict[str, str]]:
    return [
        {
            "id": preset_name,
            **strategy_source_preset_copy(preset_name),
        }
        for preset_name in strategy_source_preset_names(include_hidden=include_hidden)
    ]


def build_preset_strategy_source(
    name: str = DEFAULT_STRATEGY_SOURCE_PRESET,
    *,
    role_models: dict[str, str] | None = None,
) -> dict:
    preset_name = str(name or DEFAULT_STRATEGY_SOURCE_PRESET).strip() or DEFAULT_STRATEGY_SOURCE_PRESET
    if preset_name not in STRATEGY_SOURCE_PRESETS:
        raise WorkflowError(f"unknown workflow preset: {preset_name}")
    overrides = normalize_strategy_role_models(role_models)
    preset = json.loads(json.dumps(STRATEGY_SOURCE_PRESETS[preset_name]["workflow"], ensure_ascii=False))
    for role in preset["roles"]:
        override = overrides.get(role["id"]) or overrides.get(role["archetype"])
        if override:
            role["model"] = override
    workflow = {
        "version": 1,
        "preset": preset_name,
        "collaboration_intent": str(preset.get("collaboration_intent", "") or ""),
        "roles": preset["roles"],
        "steps": preset["steps"],
    }
    if preset.get("controls"):
        workflow["controls"] = list(preset.get("controls") or [])
    return workflow


workflow_preset_copy = strategy_source_preset_copy
workflow_preset_options = strategy_source_preset_options


def build_preset_workflow(name: str = DEFAULT_WORKFLOW_PRESET, *, role_models: dict[str, str] | None = None) -> dict:
    return build_preset_strategy_source(name, role_models=role_models)
