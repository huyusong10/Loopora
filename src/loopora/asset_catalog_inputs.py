from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, cast


@dataclass(frozen=True, kw_only=True)
class RoleDefinitionPayloadInput:
    name: str
    archetype: str
    prompt_markdown: str
    description: str = ""
    posture_notes: str = ""
    prompt_ref: str = ""
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    command_cli: str = ""
    command_args_text: str = ""
    model: str = ""
    reasoning_effort: str = ""
    role_definition_id: str = ""
    existing_prompt_ref: str = ""


@dataclass(frozen=True, kw_only=True)
class OrchestrationPayloadInput:
    name: str
    description: str = ""
    strategy_source: dict | None = None
    prompt_files: dict | None = None
    role_models: dict | None = None

    @property
    def workflow(self) -> dict | None:
        return self.strategy_source


def role_definition_payload_input_from_args(
    request: RoleDefinitionPayloadInput | None,
    raw_payload: dict[str, object],
    *,
    role_definition_id: str,
    existing_prompt_ref: str = "",
) -> RoleDefinitionPayloadInput:
    if request is not None:
        if raw_payload:
            raise TypeError("role definition request object cannot be combined with keyword fields")
        return replace(
            request,
            role_definition_id=role_definition_id,
            existing_prompt_ref=existing_prompt_ref,
        )

    fields = dict(raw_payload)
    payload_input = RoleDefinitionPayloadInput(
        name=_required_role_definition_field(fields, "name"),
        archetype=_required_role_definition_field(fields, "archetype"),
        prompt_markdown=_required_role_definition_field(fields, "prompt_markdown"),
        description=fields.pop("description", ""),
        posture_notes=fields.pop("posture_notes", ""),
        prompt_ref=fields.pop("prompt_ref", ""),
        executor_kind=fields.pop("executor_kind", "codex"),
        executor_mode=fields.pop("executor_mode", "preset"),
        command_cli=fields.pop("command_cli", ""),
        command_args_text=fields.pop("command_args_text", ""),
        model=fields.pop("model", ""),
        reasoning_effort=fields.pop("reasoning_effort", ""),
        role_definition_id=role_definition_id,
        existing_prompt_ref=existing_prompt_ref,
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected role definition fields: {unexpected_fields}")
    return payload_input


def orchestration_payload_input_from_args(
    request: OrchestrationPayloadInput | None,
    raw_payload: dict[str, object],
) -> OrchestrationPayloadInput:
    if request is not None:
        if raw_payload:
            raise TypeError("orchestration request object cannot be combined with keyword fields")
        return request

    fields = dict(raw_payload)
    try:
        name = fields.pop("name")
    except KeyError as exc:
        raise TypeError("missing orchestration field: name") from exc
    payload_input = OrchestrationPayloadInput(
        name=name,
        description=fields.pop("description", ""),
        strategy_source=_pop_strategy_source_payload(fields),
        prompt_files=fields.pop("prompt_files", None),
        role_models=fields.pop("role_models", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected orchestration fields: {unexpected_fields}")
    return payload_input


def strategy_source_from_legacy_fields(strategy_source: dict | None, legacy_fields: dict[str, Any]) -> dict | None:
    workflow = legacy_fields.pop("workflow", _MISSING)
    if legacy_fields:
        unexpected_fields = ", ".join(sorted(legacy_fields))
        raise TypeError(f"unexpected orchestration fields: {unexpected_fields}")
    if strategy_source is not None and workflow is not _MISSING:
        raise TypeError("orchestration fields strategy_source and workflow cannot both be provided")
    return strategy_source if workflow is _MISSING else cast(dict | None, workflow)


_MISSING = object()


def _required_role_definition_field(fields: dict[str, object], field: str) -> object:
    try:
        return fields.pop(field)
    except KeyError as exc:
        raise TypeError(f"missing role definition field: {field}") from exc


def _pop_strategy_source_payload(fields: dict[str, object]) -> object:
    strategy_source = fields.pop("strategy_source", _MISSING)
    workflow = fields.pop("workflow", _MISSING)
    if strategy_source is not _MISSING and workflow is not _MISSING:
        raise TypeError("orchestration fields strategy_source and workflow cannot both be provided")
    if strategy_source is not _MISSING:
        return strategy_source
    if workflow is not _MISSING:
        return workflow
    return None
