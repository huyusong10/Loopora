from __future__ import annotations

from loopora.executor_command_args import coerce_reasoning_effort, normalize_reasoning_effort, validate_command_args_text
from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode
from loopora.service_types import LooporaError
from loopora.strategy_source import strategy_role_uses_execution_snapshot


def resolve_runner_role_execution_settings(run: dict, step: dict, role: dict) -> dict[str, object]:
    step_model = str(step.get("model") or "").strip()
    step_inherit_session = bool(step.get("inherit_session"))
    step_extra_cli_args = str(step.get("extra_cli_args") or "").strip()
    role_model = str(role.get("model") or "").strip()

    if strategy_role_uses_execution_snapshot(role):
        executor_kind = normalize_executor_kind(role.get("executor_kind", "codex"))
        executor_mode = normalize_executor_mode(role.get("executor_mode", "preset"))
        profile = executor_profile(executor_kind)
        reasoning_effort = str(role.get("reasoning_effort") or "").strip()
        if profile.command_only and executor_mode != "command":
            raise LooporaError(f"{profile.label} only supports command mode")
        if executor_mode == "preset":
            return {
                "executor_kind": executor_kind,
                "executor_mode": executor_mode,
                "command_cli": "",
                "command_args_text": "",
                "model": step_model or role_model or profile.default_model,
                "reasoning_effort": normalize_reasoning_effort(reasoning_effort, executor_kind),
                "step_model": step_model,
                "inherit_session": step_inherit_session,
                "extra_cli_args_text": step_extra_cli_args,
            }
        command_args_text = str(role.get("command_args_text") or "")
        validate_command_args_text(command_args_text, executor_kind=executor_kind)
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": str(role.get("command_cli") or "").strip() or profile.cli_name,
            "command_args_text": command_args_text,
            "model": step_model or role_model,
            "reasoning_effort": reasoning_effort,
            "step_model": step_model,
            "inherit_session": step_inherit_session,
            "extra_cli_args_text": step_extra_cli_args,
        }

    executor_kind = normalize_executor_kind(run.get("executor_kind", "codex"))
    executor_mode = normalize_executor_mode(run.get("executor_mode", "preset"))
    profile = executor_profile(executor_kind)
    if profile.command_only and executor_mode != "command":
        raise LooporaError(f"{profile.label} only supports command mode")
    if executor_mode == "preset":
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": "",
            "command_args_text": "",
            "model": step_model or role_model or str(run.get("model") or "") or profile.default_model,
            "reasoning_effort": coerce_reasoning_effort(run.get("reasoning_effort", ""), executor_kind),
            "step_model": step_model,
            "inherit_session": step_inherit_session,
            "extra_cli_args_text": step_extra_cli_args,
        }

    command_args_text = str(run.get("command_args_text") or "")
    validate_command_args_text(command_args_text, executor_kind=executor_kind)
    return {
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "command_cli": str(run.get("command_cli") or "").strip() or profile.cli_name,
        "command_args_text": command_args_text,
        "model": step_model or role_model or str(run.get("model") or ""),
        "reasoning_effort": str(run.get("reasoning_effort") or "").strip(),
        "step_model": step_model,
        "inherit_session": step_inherit_session,
        "extra_cli_args_text": step_extra_cli_args,
    }
