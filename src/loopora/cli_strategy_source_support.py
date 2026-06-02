from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.service import LooporaError
from loopora.strategy_source import (
    STRATEGY_PROMPT_FILES,
    builtin_strategy_prompt_markdown,
    load_strategy_prompt_file,
    load_strategy_source_file,
    normalize_strategy_archetype,
    normalize_strategy_role_models,
    strategy_source_from_record,
)


def command_args_text_from_values(values: list[str] | None) -> str:
    if not values:
        return ""
    return "\n".join(item for item in values if item.strip())


def parse_role_models(values: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not values:
        return parsed
    for item in values:
        if "=" not in item:
            raise LooporaError(f"invalid --role-model value: {item}")
        role, model = item.split("=", 1)
        parsed[role.strip()] = model.strip()
    return normalize_strategy_role_models(parsed)


def strategy_source_bundle_from_entity(entity: dict[str, object]) -> tuple[dict | None, dict[str, str]]:
    strategy_source = strategy_source_from_record(entity)
    prompt_files = entity.get("prompt_files_json") or entity.get("prompt_files") or {}
    if isinstance(prompt_files, dict):
        return strategy_source, dict(prompt_files)
    return strategy_source, {}


@dataclass(frozen=True)
class RoleDefinitionBuildRequest:
    archetype: str
    prompt_file: Path | None
    prompt_template: str
    locale: str
    posture_notes: str
    executor_kind: str
    executor_mode: str
    command_cli: str
    command_arg: list[str] | None
    model: str
    reasoning_effort: str
    fallback: dict[str, object] | None = None


@dataclass(frozen=True)
class LoopBuildRequest:
    spec: Path
    workdir: Path
    executor_kind: str
    executor_mode: str
    model: str
    reasoning_effort: str
    completion_mode: str
    iteration_interval_seconds: float
    command_cli: str
    command_arg: list[str] | None
    max_iters: int
    max_role_retries: int
    delta_threshold: float
    trigger_window: int
    regression_window: int
    name: str | None
    role_model: list[str] | None
    orchestration_id: str
    strategy_preset: str
    strategy_file: Path | None


def resolve_strategy_source_bundle(
    *,
    strategy_file: Path | None,
    strategy_preset: str,
    fallback_strategy_source: dict | None = None,
    fallback_prompt_files: dict[str, str] | None = None,
) -> tuple[dict | None, dict[str, str]]:
    strategy_source = fallback_strategy_source
    prompt_files = dict(fallback_prompt_files or {})
    if strategy_file is not None:
        loaded_strategy_source, loaded_prompt_files = load_strategy_source_file(strategy_file)
        return loaded_strategy_source, dict(loaded_prompt_files or {})
    if strategy_preset.strip():
        return {"preset": strategy_preset.strip()}, {}
    return strategy_source, prompt_files


def read_prompt_markdown(
    *,
    prompt_file: Path | None,
    prompt_template: str,
    locale: str,
    archetype: str,
    fallback: str = "",
) -> str:
    if prompt_file is not None:
        return load_strategy_prompt_file(prompt_file)
    if prompt_template.strip():
        return builtin_strategy_prompt_markdown(prompt_template.strip(), locale=locale)
    if fallback:
        return fallback
    normalized_archetype = normalize_strategy_archetype(archetype)
    return builtin_strategy_prompt_markdown(STRATEGY_PROMPT_FILES[normalized_archetype], locale=locale)


def build_role_definition_kwargs(
    request: RoleDefinitionBuildRequest,
) -> dict[str, str]:
    current = request.fallback or {}
    normalized_archetype = normalize_strategy_archetype(
        request.archetype or str(current.get("archetype", "builder") or "builder")
    )
    prompt_markdown = read_prompt_markdown(
        prompt_file=request.prompt_file,
        prompt_template=request.prompt_template,
        locale=request.locale,
        archetype=normalized_archetype,
        fallback=str(current.get("prompt_markdown", "")),
    )
    return {
        "archetype": normalized_archetype,
        "prompt_markdown": prompt_markdown,
        "posture_notes": request.posture_notes or str(current.get("posture_notes", "")),
        "executor_kind": request.executor_kind or str(current.get("executor_kind", "codex") or "codex"),
        "executor_mode": request.executor_mode or str(current.get("executor_mode", "preset") or "preset"),
        "command_cli": request.command_cli or str(current.get("command_cli", "")),
        "command_args_text": command_args_text_from_values(request.command_arg)
        if request.command_arg is not None
        else str(current.get("command_args_text", "")),
        "model": request.model or str(current.get("model", "")),
        "reasoning_effort": request.reasoning_effort or str(current.get("reasoning_effort", "")),
    }


def build_loop_kwargs(
    request: LoopBuildRequest,
) -> dict[str, object]:
    strategy_source: dict | None = None
    prompt_files: dict[str, str] | None = None
    if request.strategy_file is not None:
        strategy_source, prompt_files = load_strategy_source_file(request.strategy_file)
    elif request.strategy_preset and not request.orchestration_id.strip():
        strategy_source = {"preset": request.strategy_preset}
    return {
        "name": request.name or request.workdir.resolve().name,
        "spec_path": request.spec,
        "workdir": request.workdir,
        "orchestration_id": request.orchestration_id.strip() or None,
        "executor_kind": request.executor_kind,
        "executor_mode": request.executor_mode,
        "command_cli": request.command_cli,
        "command_args_text": command_args_text_from_values(request.command_arg),
        "model": request.model,
        "reasoning_effort": request.reasoning_effort,
        "completion_mode": request.completion_mode,
        "iteration_interval_seconds": request.iteration_interval_seconds,
        "max_iters": request.max_iters,
        "max_role_retries": request.max_role_retries,
        "delta_threshold": request.delta_threshold,
        "trigger_window": request.trigger_window,
        "regression_window": request.regression_window,
        "workflow": strategy_source,
        "prompt_files": prompt_files,
        "role_models": parse_role_models(request.role_model),
    }
