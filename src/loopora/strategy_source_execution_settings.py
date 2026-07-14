from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.loop_compose_validation import default_loop_role_execution_options, normalize_loop_role_execution_options
from loopora.strategy_source_constants import ROLE_EXECUTION_FIELDS


def default_strategy_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    try:
        execution_options = default_loop_role_execution_options(executor_kind)
    except ValueError as exc:
        raise ValueError(_strategy_role_execution_settings_error_message(str(exc))) from exc
    return {
        "executor_kind": execution_options.executor_kind,
        "executor_mode": execution_options.executor_mode,
        "command_cli": execution_options.command_cli,
        "command_args_text": execution_options.command_args_text,
        "model": execution_options.model,
        "reasoning_effort": execution_options.reasoning_effort,
    }


def default_role_execution_settings(executor_kind: str = "codex") -> dict[str, str]:
    return default_strategy_role_execution_settings(executor_kind)


def normalize_strategy_role_execution_settings(
    raw_settings: Mapping[str, Any] | None = None,
    *,
    default_executor_kind: str = "codex",
) -> dict[str, str]:
    settings = dict(raw_settings or {})
    try:
        execution_options = normalize_loop_role_execution_options(
            executor_kind=str(settings.get("executor_kind", default_executor_kind)).strip() or default_executor_kind,
            executor_mode=str(settings.get("executor_mode", "preset")).strip() or "preset",
            command_cli=str(settings.get("command_cli", "")).strip(),
            command_args_text=str(settings.get("command_args_text", "")),
            model=str(settings.get("model", "")).strip(),
            reasoning_effort=str(settings.get("reasoning_effort", "")).strip(),
        )
    except ValueError as exc:
        raise ValueError(_strategy_role_execution_settings_error_message(str(exc))) from exc
    return {
        "executor_kind": execution_options.executor_kind,
        "executor_mode": execution_options.executor_mode,
        "command_cli": execution_options.command_cli,
        "command_args_text": execution_options.command_args_text,
        "model": execution_options.model,
        "reasoning_effort": execution_options.reasoning_effort,
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


def _strategy_role_execution_settings_error_message(message: str) -> str:
    replacements = {
        "invalid --executor:": "",
        "invalid --executor-mode:": "",
        "invalid --reasoning-effort:": "",
        "invalid --command-arg:": "",
        "invalid --completion-mode:": "",
    }
    for cli_prefix, replacement in replacements.items():
        if message.startswith(cli_prefix):
            return f"{replacement}{message[len(cli_prefix):]}".strip()
    return message
