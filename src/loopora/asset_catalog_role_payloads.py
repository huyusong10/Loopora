from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from loopora.asset_catalog_inputs import RoleDefinitionPayloadInput
from loopora.strategy_source import (
    StrategySourceError,
    normalize_strategy_archetype,
    normalize_strategy_prompt_ref,
    normalize_strategy_role_execution_settings,
    validate_strategy_prompt_markdown,
)


def normalize_role_definition_payload(payload_input: RoleDefinitionPayloadInput) -> dict:
    normalized = {
        "name": str(payload_input.name).strip(),
        "description": str(payload_input.description).strip(),
        "prompt_markdown": str(payload_input.prompt_markdown),
        "posture_notes": str(payload_input.posture_notes or "").strip(),
    }
    if not normalized["name"]:
        raise ValueError("name is required")
    normalized["archetype"] = normalize_strategy_archetype(payload_input.archetype)
    resolved_prompt_ref = (
        str(payload_input.prompt_ref).strip()
        or str(payload_input.existing_prompt_ref).strip()
        or _auto_prompt_ref(
            name=normalized["name"],
            archetype=normalized["archetype"],
            role_definition_id=payload_input.role_definition_id,
        )
    )
    normalized["prompt_ref"] = normalize_strategy_prompt_ref(resolved_prompt_ref)
    validate_strategy_prompt_markdown(normalized["prompt_markdown"], expected_archetype=normalized["archetype"])
    normalized.update(
        normalize_strategy_role_execution_settings(
            {
                "executor_kind": payload_input.executor_kind,
                "executor_mode": payload_input.executor_mode,
                "command_cli": payload_input.command_cli,
                "command_args_text": payload_input.command_args_text,
                "model": payload_input.model,
                "reasoning_effort": payload_input.reasoning_effort,
            }
        )
    )
    return normalized


def ensure_unique_role_definition_prompt_ref(
    prompt_ref: str,
    *,
    builtin_records: Iterable[Mapping[str, object]],
    custom_records: Iterable[Mapping[str, object]],
    exclude_role_definition_id: str = "",
) -> None:
    try:
        normalized_prompt_ref = normalize_strategy_prompt_ref(prompt_ref)
    except StrategySourceError as exc:
        raise ValueError(str(exc)) from exc
    excluded_id = str(exclude_role_definition_id or "").strip()
    for record in builtin_records:
        if record["id"] != excluded_id and str(record.get("prompt_ref", "")).strip() == normalized_prompt_ref:
            raise ValueError(f"prompt_ref already in use: {normalized_prompt_ref}")
    for record in custom_records:
        if record["id"] != excluded_id and str(record.get("prompt_ref", "")).strip() == normalized_prompt_ref:
            raise ValueError(f"prompt_ref already in use: {normalized_prompt_ref}")


def _auto_prompt_ref(*, name: str, archetype: str, role_definition_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")
    if not slug:
        slug = archetype
    suffix = str(role_definition_id).split("_")[-1]
    return f"{slug}-{suffix}.md"
