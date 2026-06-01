from __future__ import annotations

from dataclasses import dataclass

from loopora.executor_command_args import validate_command_args_text
from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode, normalize_reasoning_setting
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
        kind = normalize_executor_kind(request.executor_kind)
        profile = executor_profile(kind)
        mode = "command" if profile.command_only else normalize_executor_mode(request.executor_mode)
        if mode == "preset":
            return {
                "executor_kind": kind,
                "executor_mode": mode,
                "command_cli": "",
                "command_args_text": "",
                "model": str(request.model or profile.default_model or "").strip(),
                "reasoning_effort": normalize_reasoning_setting(request.reasoning_effort, executor_kind=kind),
            }
        normalized_cli = str(request.command_cli or profile.cli_name or "").strip()
        validate_command_args_text(request.command_args_text, executor_kind=kind)
        return {
            "executor_kind": kind,
            "executor_mode": mode,
            "command_cli": normalized_cli,
            "command_args_text": str(request.command_args_text or ""),
            "model": str(request.model or "").strip(),
            "reasoning_effort": str(request.reasoning_effort or "").strip(),
        }
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc
