from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from loopora.asset_catalog_role_snapshots import hydrate_strategy_role_snapshots
from loopora.strategy_source import (
    normalize_strategy_source,
    resolve_strategy_prompt_files,
    strategy_source_from_record,
)


@dataclass(frozen=True)
class OrchestrationResolutionRequest:
    orchestration_id: str | None
    workflow: dict | None
    prompt_files: dict | None
    role_models: dict | None
    builtin_orchestrations: list[dict]
    get_orchestration: Callable[[str], dict]
    get_role_definition: Callable[[str], dict]
    not_found_errors: tuple[type[Exception], ...] = ()


def resolve_orchestration_input(request: OrchestrationResolutionRequest) -> dict:
    orchestration_id = request.orchestration_id
    workflow = request.workflow
    prompt_files = request.prompt_files
    role_models = request.role_models
    builtin_orchestrations = request.builtin_orchestrations
    get_orchestration = request.get_orchestration
    not_found_errors = request.not_found_errors

    if orchestration_id and workflow is None and not prompt_files:
        orchestration = request.get_orchestration(orchestration_id)
        hydrated_strategy_source, hydrated_prompt_files = hydrate_strategy_role_snapshots(
            strategy_source_from_record(orchestration) or {},
            orchestration.get("prompt_files_json") or {},
            get_role_definition=request.get_role_definition,
        )
        normalized_strategy_source = normalize_strategy_source(hydrated_strategy_source, role_models=role_models)
        resolved_prompt_files = resolve_strategy_prompt_files(
            normalized_strategy_source,
            hydrated_prompt_files,
        )
        return {
            "id": orchestration["id"],
            "name": orchestration["name"],
            "workflow": normalized_strategy_source,
            "prompt_files": resolved_prompt_files,
        }

    hydrated_strategy_source, hydrated_prompt_files = hydrate_strategy_role_snapshots(
        workflow,
        prompt_files,
        get_role_definition=request.get_role_definition,
    )
    normalized_strategy_source = normalize_strategy_source(hydrated_strategy_source, role_models=role_models)
    resolved_prompt_files = resolve_strategy_prompt_files(normalized_strategy_source, hydrated_prompt_files)
    derived_id = str(orchestration_id or "").strip()
    derived_name = _orchestration_name_for_id(
        derived_id,
        get_orchestration=get_orchestration,
        not_found_errors=not_found_errors,
    )
    if not derived_id and normalized_strategy_source.get("preset"):
        derived_id = f"builtin:{normalized_strategy_source['preset']}"
        derived_name = _builtin_orchestration_name(
            derived_id,
            builtin_orchestrations=builtin_orchestrations,
            default_name=normalized_strategy_source["preset"],
        )
    return {
        "id": derived_id,
        "name": derived_name,
        "workflow": normalized_strategy_source,
        "prompt_files": resolved_prompt_files,
    }


def _orchestration_name_for_id(
    orchestration_id: str,
    *,
    get_orchestration: Callable[[str], dict],
    not_found_errors: tuple[type[Exception], ...],
) -> str:
    if not orchestration_id:
        return ""
    try:
        return str(get_orchestration(orchestration_id).get("name") or "")
    except not_found_errors:
        return ""


def _builtin_orchestration_name(
    orchestration_id: str,
    *,
    builtin_orchestrations: list[dict],
    default_name: object,
) -> str:
    return next(
        (
            str(record.get("name") or "")
            for record in builtin_orchestrations
            if record.get("id") == orchestration_id
        ),
        str(default_name),
    )
