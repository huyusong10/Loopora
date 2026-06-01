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
