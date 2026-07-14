from __future__ import annotations

from dataclasses import dataclass

from loopora.loop_compose_validation import normalize_loop_compose_execution_options
from loopora.service_types import LooporaError


@dataclass(frozen=True)
class AlignmentExecutorSettingsRequest:
    executor_kind: str
    executor_mode: str
    command_cli: str
    command_args_text: str
    model: str
    reasoning_effort: str


def default_alignment_executor_settings() -> AlignmentExecutorSettingsRequest:
    return AlignmentExecutorSettingsRequest(
        executor_kind="codex",
        executor_mode="preset",
        command_cli="",
        command_args_text="",
        model="",
        reasoning_effort="",
    )


def alignment_executor_settings_from_raw(raw_request: dict[str, object]) -> AlignmentExecutorSettingsRequest:
    default_settings = default_alignment_executor_settings()
    return AlignmentExecutorSettingsRequest(
        executor_kind=str(raw_request.get("executor_kind", default_settings.executor_kind) or default_settings.executor_kind).strip(),
        executor_mode=str(raw_request.get("executor_mode", default_settings.executor_mode) or default_settings.executor_mode).strip(),
        command_cli=str(raw_request.get("command_cli", default_settings.command_cli) or default_settings.command_cli).strip(),
        command_args_text=str(raw_request.get("command_args_text", default_settings.command_args_text) or default_settings.command_args_text),
        model=str(raw_request.get("model", default_settings.model) or default_settings.model).strip(),
        reasoning_effort=str(raw_request.get("reasoning_effort", default_settings.reasoning_effort) or default_settings.reasoning_effort).strip(),
    )


def normalize_alignment_executor_settings(request: AlignmentExecutorSettingsRequest) -> dict:
    try:
        settings = normalize_loop_compose_execution_options(
            executor_kind=request.executor_kind,
            executor_mode=request.executor_mode,
            reasoning_effort=request.reasoning_effort,
            completion_mode="gatekeeper",
            command_cli=request.command_cli,
            command_args_text=request.command_args_text,
            model=request.model,
            force_command_mode_for_command_only_executor=True,
        )
        return {
            "executor_kind": settings.executor_kind,
            "executor_mode": settings.executor_mode,
            "command_cli": settings.command_cli,
            "command_args_text": settings.command_args_text,
            "model": settings.model,
            "reasoning_effort": settings.reasoning_effort,
        }
    except ValueError as exc:
        raise LooporaError(_alignment_executor_settings_error_message(str(exc))) from exc


def _alignment_executor_settings_error_message(message: str) -> str:
    replacements = {
        "invalid --executor:": "invalid executor_kind:",
        "invalid --executor-mode:": "invalid executor_mode:",
        "invalid --reasoning-effort:": "invalid reasoning_effort:",
        "invalid --command-arg:": "invalid command_args_text:",
    }
    for cli_prefix, field_prefix in replacements.items():
        if message.startswith(cli_prefix):
            return f"{field_prefix}{message[len(cli_prefix):]}"
    return message
