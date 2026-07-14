from __future__ import annotations

from loopora.loop_compose_validation import normalize_loop_compose_execution_options
from loopora.service_types import LooporaError
from loopora.strategy_source import strategy_role_uses_execution_snapshot


def resolve_runner_role_execution_settings(run: dict, step: dict, role: dict) -> dict[str, object]:
    step_model = str(step.get("model") or "").strip()
    step_inherit_session = bool(step.get("inherit_session"))
    step_extra_cli_args = str(step.get("extra_cli_args") or "").strip()
    role_model = str(role.get("model") or "").strip()

    if strategy_role_uses_execution_snapshot(role):
        execution_options = _normalize_runner_execution_options(
            executor_kind=role.get("executor_kind", "codex"),
            executor_mode=role.get("executor_mode", "preset"),
            command_cli=role.get("command_cli", ""),
            command_args_text=role.get("command_args_text", ""),
            model=role_model,
            reasoning_effort=role.get("reasoning_effort", ""),
            coerce_invalid_reasoning_effort=False,
        )
        if step_model:
            execution_options["model"] = step_model
        return _with_step_runtime_fields(
            execution_options,
            step_model=step_model,
            inherit_session=step_inherit_session,
            extra_cli_args_text=step_extra_cli_args,
        )

    execution_options = _normalize_runner_execution_options(
        executor_kind=run.get("executor_kind", "codex"),
        executor_mode=run.get("executor_mode", "preset"),
        command_cli=run.get("command_cli", ""),
        command_args_text=run.get("command_args_text", ""),
        model=str(run.get("model") or ""),
        reasoning_effort=run.get("reasoning_effort", ""),
        coerce_invalid_reasoning_effort=True,
    )
    if step_model or role_model:
        execution_options["model"] = step_model or role_model
    return _with_step_runtime_fields(
        execution_options,
        step_model=step_model,
        inherit_session=step_inherit_session,
        extra_cli_args_text=step_extra_cli_args,
    )


def _normalize_runner_execution_options(  # noqa: PLR0913 - mirrors shared execution settings plus runner compatibility mode.
    *,
    executor_kind: object,
    executor_mode: object,
    command_cli: object,
    command_args_text: object,
    model: object,
    reasoning_effort: object,
    coerce_invalid_reasoning_effort: bool,
) -> dict[str, object]:
    try:
        execution_options = normalize_loop_compose_execution_options(
            executor_kind=executor_kind,
            executor_mode=executor_mode,
            reasoning_effort=reasoning_effort,
            completion_mode="gatekeeper",
            command_cli=command_cli,
            command_args_text=command_args_text,
            model=model,
            coerce_invalid_reasoning_effort=coerce_invalid_reasoning_effort,
        )
    except ValueError as exc:
        raise LooporaError(_runner_execution_settings_error_message(str(exc))) from exc
    return {
        "executor_kind": execution_options.executor_kind,
        "executor_mode": execution_options.executor_mode,
        "command_cli": execution_options.command_cli,
        "command_args_text": execution_options.command_args_text,
        "model": execution_options.model,
        "reasoning_effort": execution_options.reasoning_effort,
    }


def _with_step_runtime_fields(
    execution_options: dict[str, object],
    *,
    step_model: str,
    inherit_session: bool,
    extra_cli_args_text: str,
) -> dict[str, object]:
    return {
        **execution_options,
        "step_model": step_model,
        "inherit_session": inherit_session,
        "extra_cli_args_text": extra_cli_args_text,
    }


def _runner_execution_settings_error_message(message: str) -> str:
    replacements = {
        "invalid --executor:": "",
        "invalid --executor-mode:": "",
        "invalid --reasoning-effort:": "",
        "invalid --command-arg:": "",
    }
    for cli_prefix, replacement in replacements.items():
        if message.startswith(cli_prefix):
            return f"{replacement}{message[len(cli_prefix):]}".strip()
    return message
