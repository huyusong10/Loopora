from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_contract import BundleError
from loopora.bundle_loop_settings import normalize_bundle_completion_mode
from loopora.executor_command_args import validate_extra_cli_args_text
from loopora.strategy_source import (
    StrategySourceError,
    default_strategy_step_execution_settings,
    normalize_strategy_source_controls,
    normalize_strategy_source_identifier,
    normalize_strategy_source_version,
    normalize_strategy_step_action_policy,
    normalize_strategy_step_inherit_session,
    normalize_strategy_step_inputs,
    normalize_strategy_step_on_pass,
    normalize_strategy_step_parallel_group,
    validate_strategy_source_parallel_groups,
)


def normalize_bundle_workflow(raw_workflow: object, *, role_definitions: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw_workflow, Mapping):
        raise BundleError("bundle workflow must be an object")
    payload = dict(raw_workflow)
    raw_roles, raw_steps = _require_bundle_workflow_entries(payload)

    role_keys = {item["key"] for item in role_definitions}
    archetype_by_key = {item["key"]: item["archetype"] for item in role_definitions}
    roles, archetype_lookup = _normalize_bundle_workflow_roles(
        raw_roles,
        role_keys=role_keys,
        archetype_by_key=archetype_by_key,
    )
    steps = _normalize_bundle_workflow_steps(raw_steps, archetype_lookup=archetype_lookup)
    workflow_role_by_id = _bundle_workflow_role_archetypes(archetype_lookup)
    controls = _normalize_bundle_workflow_controls(payload.get("controls"), steps=steps, role_by_id=workflow_role_by_id)
    try:
        version = normalize_strategy_source_version(payload.get("version"), field_name="bundle workflow version")
    except StrategySourceError as exc:
        raise BundleError(str(exc)) from exc
    workflow = {
        "version": version,
        "preset": str(payload.get("preset", "") or "").strip(),
        "collaboration_intent": str(payload.get("collaboration_intent", "") or "").strip(),
        "roles": roles,
        "steps": steps,
    }
    if controls:
        workflow["controls"] = controls
    return workflow


def _require_bundle_workflow_entries(payload: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    raw_roles = payload.get("roles")
    raw_steps = payload.get("steps")
    if not isinstance(raw_roles, list) or not raw_roles:
        raise BundleError("bundle workflow.roles must be a non-empty array")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise BundleError("bundle workflow.steps must be a non-empty array")
    return raw_roles, raw_steps


def _normalize_bundle_workflow_roles(
    raw_roles: list[Any],
    *,
    role_keys: set[str],
    archetype_by_key: Mapping[str, str],
) -> tuple[list[dict[str, str]], dict[str, str]]:
    roles: list[dict[str, str]] = []
    seen_role_ids: set[str] = set()
    archetype_lookup: dict[str, str] = {}
    for index, raw_role in enumerate(raw_roles, start=1):
        role = _normalize_bundle_workflow_role(raw_role, index=index, role_keys=role_keys, seen_role_ids=seen_role_ids)
        roles.append({"id": role["id"], "role_definition_key": role["role_definition_key"]})
        archetype_lookup[role["id"]] = archetype_by_key[role["role_definition_key"]]
    return roles, archetype_lookup


def _normalize_bundle_workflow_role(
    raw_role: object,
    *,
    index: int,
    role_keys: set[str],
    seen_role_ids: set[str],
) -> dict[str, str]:
    if not isinstance(raw_role, Mapping):
        raise BundleError("bundle workflow.roles entries must be objects")
    entry = dict(raw_role)
    role_id = _bundle_workflow_identifier(
        entry.get("id") or f"role_{index:03d}",
        field_name="bundle workflow role id",
    )
    if role_id in seen_role_ids:
        raise BundleError(f"duplicate bundle workflow role id: {role_id}")
    seen_role_ids.add(role_id)
    role_key = str(entry.get("role_definition_key", "") or role_id).strip()
    if role_key not in role_keys:
        raise BundleError(f"bundle workflow role {role_id} references unknown role_definition_key: {role_key}")
    return {"id": role_id, "role_definition_key": role_key}


def _normalize_bundle_workflow_steps(
    raw_steps: list[Any],
    *,
    archetype_lookup: Mapping[str, str],
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    seen_step_ids: set[str] = set()
    for index, raw_step in enumerate(raw_steps, start=1):
        steps.append(
            _normalize_bundle_workflow_step(
                raw_step,
                index=index,
                archetype_lookup=archetype_lookup,
                seen_step_ids=seen_step_ids,
            )
        )
    return steps


def _normalize_bundle_workflow_step(
    raw_step: object,
    *,
    index: int,
    archetype_lookup: Mapping[str, str],
    seen_step_ids: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_step, Mapping):
        raise BundleError("bundle workflow.steps entries must be objects")
    entry = dict(raw_step)
    step_id = _bundle_workflow_identifier(
        entry.get("id") or f"step_{index:03d}",
        field_name="bundle workflow step id",
    )
    if step_id in seen_step_ids:
        raise BundleError(f"duplicate bundle workflow step id: {step_id}")
    seen_step_ids.add(step_id)
    role_id = _bundle_workflow_identifier(entry.get("role_id"), field_name="bundle workflow step role_id")
    if role_id not in archetype_lookup:
        raise BundleError(f"bundle workflow step references unknown role_id: {role_id}")
    return _normalize_bundle_workflow_step_payload(
        entry,
        step_id=step_id,
        role_id=role_id,
        archetype=archetype_lookup[role_id],
    )


def _normalize_bundle_workflow_step_payload(
    entry: Mapping[str, Any],
    *,
    step_id: str,
    role_id: str,
    archetype: str,
) -> dict[str, Any]:
    defaults = default_strategy_step_execution_settings(archetype=archetype)
    try:
        on_pass = normalize_strategy_step_on_pass(entry.get("on_pass"), archetype=archetype, default=defaults["on_pass"])
        inherit_session = normalize_strategy_step_inherit_session(entry.get("inherit_session"), archetype=archetype)
        action_policy = normalize_strategy_step_action_policy(
            entry.get("action_policy"),
            archetype=archetype,
            on_pass=on_pass,
        )
        extra_cli_args = str(entry.get("extra_cli_args", "") or "").strip()
        validate_extra_cli_args_text(extra_cli_args)
        parallel_group = normalize_strategy_step_parallel_group(entry.get("parallel_group"))
        inputs = normalize_strategy_step_inputs(entry.get("inputs"))
    except (StrategySourceError, ValueError) as exc:
        raise BundleError(str(exc)) from exc
    step_payload = {
        "id": step_id,
        "role_id": role_id,
        "on_pass": on_pass,
        "model": str(entry.get("model", "") or "").strip(),
        "inherit_session": inherit_session,
        "extra_cli_args": extra_cli_args,
        "action_policy": action_policy,
    }
    if parallel_group:
        step_payload["parallel_group"] = parallel_group
    if inputs:
        step_payload["inputs"] = inputs
    return step_payload


def _bundle_workflow_role_archetypes(archetype_lookup: Mapping[str, str]) -> dict[str, dict[str, str]]:
    return {role_id: {"archetype": archetype} for role_id, archetype in archetype_lookup.items()}


def _normalize_bundle_workflow_controls(
    raw_controls: object,
    *,
    steps: list[dict[str, Any]],
    role_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    try:
        validate_strategy_source_parallel_groups(steps, role_by_id)
        return normalize_strategy_source_controls(raw_controls, role_by_id=role_by_id)
    except StrategySourceError as exc:
        raise BundleError(str(exc)) from exc


def _bundle_workflow_identifier(value: object, *, field_name: str) -> str:
    try:
        return normalize_strategy_source_identifier(value, field_name=field_name)
    except StrategySourceError as exc:
        raise BundleError(str(exc)) from exc


def validate_bundle_runtime_contract(
    *,
    loop: Mapping[str, Any],
    role_definitions: list[dict[str, Any]],
    workflow: Mapping[str, Any],
) -> None:
    completion_mode = normalize_bundle_completion_mode(loop.get("completion_mode"))
    if completion_mode != "gatekeeper":
        return
    role_key_archetype = {item["key"]: item["archetype"] for item in role_definitions}
    workflow_role_archetype = {
        role["id"]: role_key_archetype.get(role["role_definition_key"], "") for role in workflow.get("roles", []) if isinstance(role, Mapping)
    }
    has_finishing_gatekeeper = any(
        workflow_role_archetype.get(str(step.get("role_id", ""))) == "gatekeeper" and str(step.get("on_pass", "") or "") == "finish_run"
        for step in workflow.get("steps", [])
        if isinstance(step, Mapping)
    )
    if not has_finishing_gatekeeper:
        raise BundleError("gatekeeper completion mode requires a GateKeeper step that can finish the run")
