from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from loopora.service import LooporaError
from loopora.strategy_source import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    build_preset_strategy_source,
    normalize_strategy_role_models,
    normalize_strategy_source,
    resolve_strategy_prompt_files,
    strategy_source_from_record,
)


@dataclass(frozen=True)
class SpecTemplateStrategyCandidate:
    present: bool
    strategy_source: dict | None


DEFAULT_ORCHESTRATION_FORM = {
    "name": "",
    "description": "",
    "workflow_preset": "",
    "strategy_json": "",
    "workflow_json": "",
    "prompt_files_json": "",
}


def _orchestration_payload_from_mapping(
    payload: Mapping[str, object],
    *,
    default_to_preset: bool = True,
) -> dict[str, object]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    if not name:
        raise LooporaError("name is required")
    return {
        "name": name,
        "description": description,
        "strategy_source": _strategy_source_from_mapping(payload, default_to_preset=default_to_preset),
        "prompt_files": _prompt_files_from_mapping(payload),
        "role_models": _role_models_from_mapping(payload),
    }


def _mapping_from_json_field(value: object, *, field_name: str) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LooporaError(f"{field_name} must be valid JSON") from exc
    if not isinstance(parsed, Mapping):
        raise LooporaError(f"{field_name} must decode to an object")
    return dict(parsed)


def _strategy_source_mapping_field(payload: Mapping[str, object]) -> SpecTemplateStrategyCandidate:
    for key in ("strategy_source", "strategy", "workflow"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return SpecTemplateStrategyCandidate(present=True, strategy_source=dict(value))
    return SpecTemplateStrategyCandidate(present=False, strategy_source=None)


def _strategy_json_mapping_field(payload: Mapping[str, object]) -> SpecTemplateStrategyCandidate:
    for key in ("strategy_json", "workflow_json"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return SpecTemplateStrategyCandidate(present=True, strategy_source=dict(value))
    return SpecTemplateStrategyCandidate(present=False, strategy_source=None)


def _strategy_source_from_json_field(payload: Mapping[str, object]) -> dict[str, object]:
    for key in ("strategy_json", "workflow_json"):
        value = payload.get(key)
        if str(value or "").strip():
            return _mapping_from_json_field(value, field_name=key)
    return {}


def _strategy_preset_from_mapping(payload: Mapping[str, object], *, default: str = "") -> str:
    preset = str(payload.get("strategy_preset") or "").strip()
    if preset:
        return preset
    return str(payload.get("workflow_preset", default)).strip() or default


def _strategy_source_from_mapping(payload: Mapping[str, object], *, default_to_preset: bool = True) -> dict | None:
    strategy_candidate = _strategy_source_mapping_field(payload)
    if strategy_candidate.present:
        return strategy_candidate.strategy_source
    strategy_json = _strategy_json_mapping_field(payload)
    if strategy_json.present:
        return strategy_json.strategy_source
    parsed_strategy_json = _strategy_source_from_json_field(payload)
    if parsed_strategy_json:
        return parsed_strategy_json
    if not default_to_preset:
        return None
    preset = _strategy_preset_from_mapping(payload, default=DEFAULT_STRATEGY_SOURCE_PRESET)
    return build_preset_strategy_source(preset)


def _strategy_source_for_spec_template(payload: Mapping[str, object]) -> dict | None:
    result: dict | None = None
    strategy_candidate = _strategy_source_mapping_field(payload)
    if strategy_candidate.present:
        result = _normalize_spec_template_strategy_source(
            _spec_template_strategy_source_or_none(strategy_candidate.strategy_source)
        )
    else:
        result = _strategy_source_for_spec_template_without_mapping_field(payload)
    return result


def _strategy_source_for_spec_template_request(
    payload: Mapping[str, object],
    *,
    get_orchestration: Callable[[str], Mapping[str, object]],
) -> dict | None:
    if _has_explicit_strategy_source_for_spec_template(payload):
        return _strategy_source_for_spec_template(payload)
    orchestration_id = str(payload.get("orchestration_id") or "").strip()
    if orchestration_id:
        orchestration = get_orchestration(orchestration_id)
        strategy_source = strategy_source_from_record(orchestration)
        return normalize_strategy_source(strategy_source) if strategy_source else None
    return _strategy_source_for_spec_template(payload)


def _has_explicit_strategy_source_for_spec_template(payload: Mapping[str, object]) -> bool:
    if _strategy_source_mapping_field(payload).present or _strategy_json_mapping_field(payload).present:
        return True
    return any(str(payload.get(key) or "").strip() for key in ("strategy_json", "workflow_json"))


def _strategy_source_for_spec_template_without_mapping_field(payload: Mapping[str, object]) -> dict | None:
    result: dict | None = None
    strategy_json_candidate = _strategy_json_mapping_field(payload)
    if strategy_json_candidate.present:
        result = _normalize_spec_template_strategy_source(_spec_template_strategy_source_or_none(strategy_json_candidate.strategy_source))
    else:
        strategy_source_json = _strategy_source_from_json_field(payload)
        result = (
            _normalize_spec_template_strategy_source(strategy_source_json)
            if strategy_source_json
            else _preset_strategy_source_for_spec_template(payload)
        )
    return result


def _spec_template_strategy_source_or_none(strategy_source: dict | None) -> dict | None:
    if not strategy_source:
        return None
    if not strategy_source.get("roles") and not strategy_source.get("steps"):
        return None
    return strategy_source


def _normalize_spec_template_strategy_source(strategy_source: dict | None) -> dict | None:
    return normalize_strategy_source(strategy_source) if strategy_source else None


def _preset_strategy_source_for_spec_template(payload: Mapping[str, object]) -> dict | None:
    preset = _strategy_preset_from_mapping(payload)
    return build_preset_strategy_source(preset) if preset else None


def _prompt_files_from_mapping(payload: Mapping[str, object]) -> dict[str, str]:
    prompt_files = payload.get("prompt_files")
    if isinstance(prompt_files, Mapping):
        return {str(key): str(value) for key, value in dict(prompt_files).items()}
    prompt_files_json = _mapping_from_json_field(payload.get("prompt_files_json"), field_name="prompt_files_json")
    return {str(key): str(value) for key, value in prompt_files_json.items()}


def _role_models_from_mapping(payload: Mapping[str, object]) -> dict[str, str]:
    role_models = payload.get("role_models")
    if isinstance(role_models, Mapping):
        return normalize_strategy_role_models(dict(role_models))
    extracted = {}
    for role in ("builder", "inspector", "gatekeeper", "guide", "generator", "tester", "verifier", "challenger"):
        value = str(payload.get(f"role_model_{role}", "")).strip()
        if value:
            extracted[role] = value
    return normalize_strategy_role_models(extracted)


def _normalize_orchestration_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_ORCHESTRATION_FORM)
    if not values:
        strategy_json = json.dumps({"version": 1, "preset": "", "roles": [], "steps": []}, ensure_ascii=False, indent=2)
        normalized["strategy_json"] = strategy_json
        normalized["workflow_json"] = strategy_json
        normalized["prompt_files_json"] = json.dumps({}, ensure_ascii=False, indent=2)
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    if isinstance(normalized.get("strategy_json"), Mapping):
        normalized["strategy_json"] = json.dumps(normalized["strategy_json"], ensure_ascii=False, indent=2)
    if isinstance(normalized.get("workflow_json"), Mapping):
        normalized["workflow_json"] = json.dumps(normalized["workflow_json"], ensure_ascii=False, indent=2)
    if isinstance(normalized.get("prompt_files_json"), Mapping):
        normalized["prompt_files_json"] = json.dumps(normalized["prompt_files_json"], ensure_ascii=False, indent=2)
    strategy_json_text = str(normalized.get("strategy_json", "")).strip()
    workflow_json_text = str(normalized.get("workflow_json", "")).strip()
    if strategy_json_text:
        normalized["workflow_json"] = normalized["strategy_json"]
    elif workflow_json_text:
        normalized["strategy_json"] = normalized["workflow_json"]
    else:
        preset_name = _strategy_preset_from_mapping(normalized)
        if preset_name:
            strategy_source = build_preset_strategy_source(preset_name)
            strategy_json = json.dumps(strategy_source, ensure_ascii=False, indent=2)
            normalized["strategy_json"] = strategy_json
            normalized["workflow_json"] = strategy_json
            normalized["prompt_files_json"] = json.dumps(
                resolve_strategy_prompt_files(strategy_source),
                ensure_ascii=False,
                indent=2,
            )
        else:
            strategy_json = json.dumps({"version": 1, "preset": "", "roles": [], "steps": []}, ensure_ascii=False, indent=2)
            normalized["strategy_json"] = strategy_json
            normalized["workflow_json"] = strategy_json
            normalized["prompt_files_json"] = json.dumps({}, ensure_ascii=False, indent=2)
    return normalized


def _orchestration_form_values_from_record(orchestration: Mapping[str, object]) -> dict[str, object]:
    strategy_source = strategy_source_from_record(orchestration) or {}
    strategy_json = json.dumps(strategy_source, ensure_ascii=False, indent=2)
    return {
        "name": str(orchestration.get("name", "")),
        "description": str(orchestration.get("description", "")),
        "workflow_preset": str(strategy_source.get("preset", "")).strip(),
        "strategy_json": strategy_json,
        "workflow_json": strategy_json,
        "prompt_files_json": json.dumps(orchestration.get("prompt_files_json") or {}, ensure_ascii=False, indent=2),
    }
