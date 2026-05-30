from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass

from loopora.numeric_inputs import coerce_integral_number


@dataclass(frozen=True, kw_only=True)
class LoopfileExportProjectionInput:
    loop: Mapping[str, object]
    loop_id: str
    strategy_source: Mapping[str, object]
    prompt_files: Mapping[str, str]
    role_definition_by_id: Mapping[str, Mapping[str, object] | None]
    bundle_id: str = ""
    name: str | None = None
    description: str = ""
    collaboration_summary: str = ""


def build_loopfile_export_projection(request: LoopfileExportProjectionInput) -> dict[str, object]:
    roles = [role for role in list(request.strategy_source.get("roles") or []) if isinstance(role, Mapping)]
    steps = [step for step in list(request.strategy_source.get("steps") or []) if isinstance(step, Mapping)]
    return {
        "version": 1,
        "metadata": {
            "bundle_id": request.bundle_id,
            "name": request.name or str(request.loop.get("name", "") or "").strip() or request.loop_id,
            "description": request.description,
        },
        "collaboration_summary": request.collaboration_summary
        or request.description
        or str(request.loop.get("name", "") or "").strip(),
        "loop": _loopfile_loop_payload(request.loop),
        "spec": {"markdown": str(request.loop.get("spec_markdown", "") or "").strip()},
        "role_definitions": [
            _loopfile_role_definition_payload(
                role,
                prompt_files=request.prompt_files,
                role_definition_by_id=request.role_definition_by_id,
            )
            for role in roles
        ],
        "workflow": _loopfile_strategy_source_payload(request.strategy_source, roles=roles, steps=steps),
    }


def _loopfile_role_definition_payload(
    role: Mapping[str, object],
    *,
    prompt_files: Mapping[str, str],
    role_definition_by_id: Mapping[str, Mapping[str, object] | None],
) -> dict[str, str]:
    role_definition_id = str(role.get("role_definition_id", "") or "").strip()
    role_definition = role_definition_by_id.get(role_definition_id) if role_definition_id else None
    prompt_ref = str(role.get("prompt_ref", "") or (role_definition or {}).get("prompt_ref", "") or "").strip()
    prompt_markdown = str(prompt_files.get(prompt_ref, "") or "") if prompt_ref else ""
    if not prompt_markdown:
        prompt_markdown = str(role.get("prompt_markdown", "") or "")
    if not prompt_markdown and role_definition is not None:
        prompt_markdown = str(role_definition.get("prompt_markdown", "") or "")
    return {
        "key": _loopfile_role_definition_key(role.get("id", "")),
        "name": str(_role_snapshot_value(role, role_definition, "name") or "").strip(),
        "description": str((role_definition or {}).get("description", "") or role.get("description", "") or "").strip(),
        "archetype": str(_role_snapshot_value(role, role_definition, "archetype") or "").strip(),
        "prompt_ref": prompt_ref,
        "prompt_markdown": prompt_markdown,
        "posture_notes": str(_role_snapshot_value(role, role_definition, "posture_notes") or "").strip(),
        "executor_kind": str(_role_snapshot_value(role, role_definition, "executor_kind") or "").strip(),
        "executor_mode": str(_role_snapshot_value(role, role_definition, "executor_mode") or "").strip(),
        "command_cli": str(_role_snapshot_value(role, role_definition, "command_cli") or "").strip(),
        "command_args_text": str(_role_snapshot_value(role, role_definition, "command_args_text") or ""),
        "model": str(_role_snapshot_value(role, role_definition, "model") or "").strip(),
        "reasoning_effort": str(_role_snapshot_value(role, role_definition, "reasoning_effort") or "").strip(),
    }


def _loopfile_strategy_source_payload(
    strategy_source: Mapping[str, object],
    *,
    roles: list[Mapping[str, object]],
    steps: list[Mapping[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": int(strategy_source.get("version", 1) or 1),
        "preset": str(strategy_source.get("preset", "") or "").strip(),
        "collaboration_intent": str(strategy_source.get("collaboration_intent", "") or "").strip(),
        "roles": [
            {
                "id": str(role.get("id", "") or "").strip(),
                "role_definition_key": _loopfile_role_definition_key(role.get("id", "")),
            }
            for role in roles
        ],
        "steps": [_loopfile_strategy_step_payload(step) for step in steps],
    }
    if strategy_source.get("controls"):
        payload["controls"] = deepcopy(strategy_source.get("controls") or [])
    return payload


def _loopfile_strategy_step_payload(step: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": str(step.get("id", "") or "").strip(),
        "role_id": str(step.get("role_id", "") or "").strip(),
        "on_pass": str(step.get("on_pass", "continue") or "continue").strip(),
        "model": str(step.get("model", "") or "").strip(),
        "inherit_session": bool(step.get("inherit_session")),
        "extra_cli_args": str(step.get("extra_cli_args", "") or "").strip(),
        "action_policy": deepcopy(step.get("action_policy") or {}),
        **(
            {"parallel_group": str(step.get("parallel_group", "") or "").strip()}
            if str(step.get("parallel_group", "") or "").strip()
            else {}
        ),
        **({"inputs": deepcopy(step.get("inputs"))} if isinstance(step.get("inputs"), dict) and step.get("inputs") else {}),
    }


def _loopfile_loop_payload(loop: Mapping[str, object]) -> dict[str, object]:
    return {
        "name": str(loop.get("name", "") or "").strip(),
        "workdir": str(loop.get("workdir", "") or ""),
        "completion_mode": str(loop.get("completion_mode", "gatekeeper") or "gatekeeper").strip(),
        "executor_kind": str(loop.get("executor_kind", "codex") or "codex").strip(),
        "executor_mode": str(loop.get("executor_mode", "preset") or "preset").strip(),
        "command_cli": str(loop.get("command_cli", "") or "").strip(),
        "command_args_text": str(loop.get("command_args_text", "") or ""),
        "model": str(loop.get("model", "") or "").strip(),
        "reasoning_effort": str(loop.get("reasoning_effort", "") or "").strip(),
        "iteration_interval_seconds": _loop_runtime_number(
            loop,
            "iteration_interval_seconds",
            0.0,
            integer_only=False,
        ),
        "max_iters": _loop_runtime_number(loop, "max_iters", 8, integer_only=True),
        "max_role_retries": _loop_runtime_number(loop, "max_role_retries", 2, integer_only=True),
        "delta_threshold": _loop_runtime_number(loop, "delta_threshold", 0.005, integer_only=False),
        "trigger_window": _loop_runtime_number(loop, "trigger_window", 4, integer_only=True),
        "regression_window": _loop_runtime_number(loop, "regression_window", 2, integer_only=True),
    }


def _loopfile_role_definition_key(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return normalized or "role"


def _role_snapshot_value(
    role: Mapping[str, object],
    role_definition: Mapping[str, object] | None,
    field: str,
) -> object:
    return role.get(field, "") if field in role else (role_definition or {}).get(field, "")


def _loop_runtime_number(
    loop: Mapping[str, object],
    key: str,
    default: int | float,
    *,
    integer_only: bool,
) -> int | float:
    value = loop.get(key, default)
    if value is None or value == "":
        value = default
    return coerce_integral_number(value, field_name=f"loop.{key}") if integer_only else float(value)
