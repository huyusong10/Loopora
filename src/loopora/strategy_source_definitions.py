from __future__ import annotations

from collections.abc import Mapping

from typing import Any

from loopora.strategy_source_controls import normalize_strategy_source_controls

from loopora.strategy_source_errors import WorkflowError

from loopora.strategy_source_presets import DEFAULT_STRATEGY_SOURCE_PRESET, build_preset_strategy_source

from loopora.strategy_source_roles import normalize_strategy_role_models, normalize_strategy_source_roles

from loopora.strategy_source_steps import normalize_strategy_source_steps

from loopora.strategy_source_validation import normalize_strategy_source_version

"""Strategy Source warning and finish-gate detection rules."""



def strategy_source_warnings(strategy_source: dict) -> list[str]:
    role_by_id = {role["id"]: role for role in strategy_source.get("roles", [])}
    steps = list(strategy_source.get("steps", []))
    warnings: list[str] = []
    if not strategy_source_has_finish_gatekeeper_step(strategy_source):
        warnings.append(
            "This workflow has no GateKeeper finish step, so it should be paired with round-based completion or updated before gate-based execution."
        )
    warnings.extend(strategy_source_guide_input_warnings(steps, role_by_id))
    gate_before_builder = False
    gate_after_builder_without_inspector = False
    seen_builder = False
    seen_inspector_after_builder = False
    for index, step in enumerate(steps):
        role = role_by_id.get(step["role_id"], {})
        archetype = role.get("archetype")
        if archetype == "builder":
            seen_builder = True
            seen_inspector_after_builder = False
        elif archetype == "inspector" and seen_builder:
            seen_inspector_after_builder = True
        elif archetype == "gatekeeper":
            if any(
                role_by_id.get(other["role_id"], {}).get("archetype") == "builder"
                for other in steps[index + 1 :]
            ):
                gate_before_builder = True
            if seen_builder and not seen_inspector_after_builder:
                gate_after_builder_without_inspector = True
    if gate_before_builder:
        warnings.append("GateKeeper appears before a later Builder step, so it may only judge pre-change evidence.")
    if gate_after_builder_without_inspector:
        warnings.append("GateKeeper appears after Builder without a later Inspector step, so it may judge stale evidence.")
    return warnings

def workflow_warnings(workflow: dict) -> list[str]:
    return strategy_source_warnings(workflow)

def strategy_source_guide_input_warnings(
    steps: list[dict[str, Any]],
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    for step in steps:
        role = role_by_id.get(step["role_id"], {})
        if role.get("archetype") != "guide":
            continue
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        if not inputs.get("handoffs_from") or not inputs.get("evidence_query"):
            warnings.append(f"Guide step {step['id']} has incomplete upstream inputs, so it may rely on ambient context.")
    return warnings

def workflow_guide_input_warnings(
    steps: list[dict[str, Any]],
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    return strategy_source_guide_input_warnings(steps, role_by_id)

def strategy_source_has_finish_gatekeeper_step(strategy_source: dict[str, Any] | None) -> bool:
    if not strategy_source:
        return False
    role_by_id = {
        str(role.get("id", "")).strip(): role
        for role in strategy_source.get("roles", [])
        if isinstance(role, dict)
    }
    for raw_step in strategy_source.get("steps", []):
        if not isinstance(raw_step, dict):
            continue
        role = role_by_id.get(str(raw_step.get("role_id", "")).strip())
        if not role or role.get("archetype") != "gatekeeper":
            continue
        if str(raw_step.get("on_pass", "continue") or "continue").strip() == "finish_run":
            return True
    return False

def has_finish_gatekeeper_step(workflow: dict[str, Any] | None) -> bool:
    return strategy_source_has_finish_gatekeeper_step(workflow)


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

"""Strategy Source file loading and prompt-file resolution."""

import json


from pathlib import Path


import yaml


from loopora.strategy_source_prompt_assets import (
    builtin_strategy_prompt_markdown,
    normalize_prompt_ref,
    validate_prompt_markdown,
)

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
    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkflowError("workflow file must be UTF-8 encoded YAML or JSON") from exc
    suffix = path.suffix.lower()
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

"""Strategy Source definitions and legacy workflow-format compatibility rules."""

from loopora.strategy_source_constants import (
    ARCHETYPES,
    LEGACY_ROLE_BY_ARCHETYPE,
    PROMPT_FILES,
    ROLE_EXECUTION_FIELDS,
    ROLE_POSTURE_FIELDS,
    STRATEGY_SOURCE_VERSION,
)
from loopora.strategy_source_controls import (
    STRATEGY_SOURCE_CONTROL_AFTER_RE as STRATEGY_SOURCE_CONTROL_AFTER_RE,
    STRATEGY_SOURCE_CONTROL_ARCHETYPES as STRATEGY_SOURCE_CONTROL_ARCHETYPES,
    STRATEGY_SOURCE_CONTROL_CALL_KEYS as STRATEGY_SOURCE_CONTROL_CALL_KEYS,
    STRATEGY_SOURCE_CONTROL_KEYS as STRATEGY_SOURCE_CONTROL_KEYS,
    STRATEGY_SOURCE_CONTROL_MODES as STRATEGY_SOURCE_CONTROL_MODES,
    STRATEGY_SOURCE_CONTROL_SIGNALS as STRATEGY_SOURCE_CONTROL_SIGNALS,
    STRATEGY_SOURCE_CONTROL_WHEN_KEYS as STRATEGY_SOURCE_CONTROL_WHEN_KEYS,
    WORKFLOW_CONTROL_AFTER_RE as WORKFLOW_CONTROL_AFTER_RE,
    WORKFLOW_CONTROL_ARCHETYPES as WORKFLOW_CONTROL_ARCHETYPES,
    WORKFLOW_CONTROL_CALL_KEYS as WORKFLOW_CONTROL_CALL_KEYS,
    WORKFLOW_CONTROL_KEYS as WORKFLOW_CONTROL_KEYS,
    WORKFLOW_CONTROL_MODES as WORKFLOW_CONTROL_MODES,
    WORKFLOW_CONTROL_SIGNALS as WORKFLOW_CONTROL_SIGNALS,
    WORKFLOW_CONTROL_WHEN_KEYS as WORKFLOW_CONTROL_WHEN_KEYS,
    normalize_strategy_source_control as normalize_strategy_source_control,
    normalize_strategy_source_control_call as normalize_strategy_source_control_call,
    normalize_strategy_source_control_id as normalize_strategy_source_control_id,
    normalize_strategy_source_control_max_fires as normalize_strategy_source_control_max_fires,
    normalize_strategy_source_control_mode as normalize_strategy_source_control_mode,
    normalize_strategy_source_control_when as normalize_strategy_source_control_when,
    normalize_workflow_control as normalize_workflow_control,
    normalize_workflow_control_call as normalize_workflow_control_call,
    normalize_workflow_control_id as normalize_workflow_control_id,
    normalize_workflow_control_max_fires as normalize_workflow_control_max_fires,
    normalize_workflow_control_mode as normalize_workflow_control_mode,
    normalize_workflow_control_when as normalize_workflow_control_when,
    normalize_workflow_controls as normalize_workflow_controls,
)
from loopora.strategy_source_roles import (
    default_role_execution_settings as default_role_execution_settings,
    default_strategy_role_execution_settings as default_strategy_role_execution_settings,
    normalize_role_execution_settings as normalize_role_execution_settings,
    normalize_strategy_role_execution_settings as normalize_strategy_role_execution_settings,
    role_uses_execution_snapshot as role_uses_execution_snapshot,
    strategy_role_uses_execution_snapshot as strategy_role_uses_execution_snapshot,
)
from loopora.strategy_source_errors import StrategySourceError as StrategySourceError
from loopora.strategy_source_prompt_assets import (
    PROMPT_ASSET_DIR as PROMPT_ASSET_DIR,
    PROMPT_FRONT_MATTER_RE as PROMPT_FRONT_MATTER_RE,
    SPEC_PRACTICE_ASSET_DIR as SPEC_PRACTICE_ASSET_DIR,
    available_prompt_templates as available_prompt_templates,
    available_strategy_prompt_templates as available_strategy_prompt_templates,
    builtin_prompt_files_for_strategy_source as builtin_prompt_files_for_strategy_source,
    builtin_prompt_files_for_workflow as builtin_prompt_files_for_workflow,
    builtin_prompt_markdown as builtin_prompt_markdown,
    builtin_prompt_markdown_by_locale as builtin_prompt_markdown_by_locale,
    builtin_strategy_prompt_markdown_by_locale as builtin_strategy_prompt_markdown_by_locale,
    load_prompt_file as load_prompt_file,
    load_strategy_prompt_file as load_strategy_prompt_file,
    localized_prompt_ref as localized_prompt_ref,
    normalize_prompt_locale as normalize_prompt_locale,
    parse_prompt_markdown as parse_prompt_markdown,
    prompt_asset_path as prompt_asset_path,
)
from loopora.strategy_source_presets import (
    DEFAULT_WORKFLOW_PRESET as DEFAULT_WORKFLOW_PRESET,
    STRATEGY_SOURCE_PRESETS as STRATEGY_SOURCE_PRESETS,
    WORKFLOW_PRESETS as WORKFLOW_PRESETS,
    PresetRoleSpec as PresetRoleSpec,
    PresetStepSpec as PresetStepSpec,
    StrategySourcePresetDefinitionSpec as StrategySourcePresetDefinitionSpec,
    WorkflowPresetDefinitionSpec as WorkflowPresetDefinitionSpec,
    build_preset_workflow as build_preset_workflow,
    builtin_spec_practice as builtin_spec_practice,
    preset_names as preset_names,
    strategy_source_preset_copy as strategy_source_preset_copy,
    strategy_source_preset_names as strategy_source_preset_names,
    strategy_source_preset_options as strategy_source_preset_options,
    workflow_preset_copy as workflow_preset_copy,
    workflow_preset_options as workflow_preset_options,
)
from loopora.strategy_source_roles import (
    display_name_for_archetype as display_name_for_archetype,
    normalize_archetype as normalize_archetype,
    normalize_role_display_name as normalize_role_display_name,
    normalize_role_models as normalize_role_models,
    normalize_strategy_archetype as normalize_strategy_archetype,
    normalize_strategy_role_display_name as normalize_strategy_role_display_name,
    normalize_strategy_source_role as normalize_strategy_source_role,
    normalize_workflow_role as normalize_workflow_role,
    normalize_workflow_roles as normalize_workflow_roles,
    strategy_archetype_display_name as strategy_archetype_display_name,
)
from loopora.strategy_source_steps import (
    PARALLEL_GROUP_ARCHETYPES as PARALLEL_GROUP_ARCHETYPES,
    STEP_ACTION_POLICY_KEYS as STEP_ACTION_POLICY_KEYS,
    STEP_ACTION_POLICY_WORKSPACES as STEP_ACTION_POLICY_WORKSPACES,
    STEP_EVIDENCE_QUERY_KEYS as STEP_EVIDENCE_QUERY_KEYS,
    STEP_EXECUTION_FIELDS as STEP_EXECUTION_FIELDS,
    STEP_INPUT_KEYS as STEP_INPUT_KEYS,
    STEP_ITERATION_MEMORY_POLICIES as STEP_ITERATION_MEMORY_POLICIES,
    default_step_action_policy as default_step_action_policy,
    default_step_execution_settings as default_step_execution_settings,
    default_step_inherit_session as default_step_inherit_session,
    default_strategy_step_action_policy as default_strategy_step_action_policy,
    default_strategy_step_execution_settings as default_strategy_step_execution_settings,
    default_strategy_step_inherit_session as default_strategy_step_inherit_session,
    normalize_step_action_policy as normalize_step_action_policy,
    normalize_step_action_policy_workspace as normalize_step_action_policy_workspace,
    normalize_step_evidence_archetypes as normalize_step_evidence_archetypes,
    normalize_step_evidence_limit as normalize_step_evidence_limit,
    normalize_step_evidence_query as normalize_step_evidence_query,
    normalize_step_handoffs_from as normalize_step_handoffs_from,
    normalize_step_inherit_session as normalize_step_inherit_session,
    normalize_step_inputs as normalize_step_inputs,
    normalize_step_iteration_memory as normalize_step_iteration_memory,
    normalize_step_on_pass as normalize_step_on_pass,
    normalize_step_parallel_group as normalize_step_parallel_group,
    normalize_step_policy_boolean as normalize_step_policy_boolean,
    normalize_strategy_source_step as normalize_strategy_source_step,
    normalize_strategy_step_action_policy as normalize_strategy_step_action_policy,
    normalize_strategy_step_action_policy_workspace as normalize_strategy_step_action_policy_workspace,
    normalize_strategy_step_evidence_archetypes as normalize_strategy_step_evidence_archetypes,
    normalize_strategy_step_evidence_limit as normalize_strategy_step_evidence_limit,
    normalize_strategy_step_evidence_query as normalize_strategy_step_evidence_query,
    normalize_strategy_step_handoffs_from as normalize_strategy_step_handoffs_from,
    normalize_strategy_step_inherit_session as normalize_strategy_step_inherit_session,
    normalize_strategy_step_inputs as normalize_strategy_step_inputs,
    normalize_strategy_step_iteration_memory as normalize_strategy_step_iteration_memory,
    normalize_strategy_step_on_pass as normalize_strategy_step_on_pass,
    normalize_strategy_step_parallel_group as normalize_strategy_step_parallel_group,
    normalize_workflow_step as normalize_workflow_step,
    normalize_workflow_steps as normalize_workflow_steps,
    strategy_source_step_parallel_group as strategy_source_step_parallel_group,
    validate_parallel_group_contiguity as validate_parallel_group_contiguity,
    validate_parallel_group_size as validate_parallel_group_size,
    validate_parallel_group_step as validate_parallel_group_step,
    validate_strategy_source_parallel_groups as validate_strategy_source_parallel_groups,
    validate_workflow_parallel_groups as validate_workflow_parallel_groups,
    workflow_step_parallel_group as workflow_step_parallel_group,
)
from loopora.strategy_source_validation import (
    STRATEGY_SOURCE_SAFE_IDENTIFIER_RE as STRATEGY_SOURCE_SAFE_IDENTIFIER_RE,
    WORKFLOW_SAFE_IDENTIFIER_RE as WORKFLOW_SAFE_IDENTIFIER_RE,
    normalize_strategy_source_identifier as normalize_strategy_source_identifier,
    normalize_workflow_identifier as normalize_workflow_identifier,
    normalize_workflow_version as normalize_workflow_version,
)

STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES
WORKFLOW_VERSION = STRATEGY_SOURCE_VERSION
LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE
STRATEGY_PROMPT_FILES = PROMPT_FILES
STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS
STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS
