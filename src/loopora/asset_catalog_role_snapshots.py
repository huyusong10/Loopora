from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass

from loopora.strategy_source import (
    STRATEGY_ROLE_EXECUTION_FIELDS,
    STRATEGY_ROLE_POSTURE_FIELDS,
    StrategySourceError,
    normalize_strategy_archetype,
    normalize_strategy_prompt_ref,
)


@dataclass(frozen=True)
class RoleSnapshotDefinition:
    role: dict
    definition: Mapping[str, object]
    role_definition_id: str
    role_label: str


def hydrate_strategy_role_snapshots(
    strategy_source: dict | None,
    prompt_files: dict | None,
    *,
    get_role_definition: Callable[[str], Mapping[str, object]],
) -> tuple[dict | None, dict[str, str] | None]:
    if strategy_source is None:
        return None, dict(prompt_files or {}) if prompt_files is not None else None

    hydrated_strategy_source = deepcopy(strategy_source)
    raw_roles = hydrated_strategy_source.get("roles")
    if not isinstance(raw_roles, list):
        return hydrated_strategy_source, dict(prompt_files or {}) if prompt_files is not None else None

    hydrated_prompt_files = dict(prompt_files or {})
    hydrated_strategy_source["roles"] = [
        _hydrate_strategy_role_snapshot(
            raw_role,
            hydrated_prompt_files=hydrated_prompt_files,
            get_role_definition=get_role_definition,
        )
        for raw_role in raw_roles
    ]
    return hydrated_strategy_source, hydrated_prompt_files


def _hydrate_strategy_role_snapshot(
    raw_role: object,
    *,
    hydrated_prompt_files: dict[str, str],
    get_role_definition: Callable[[str], Mapping[str, object]],
) -> object:
    if not isinstance(raw_role, dict):
        return raw_role
    role = dict(raw_role)
    role_definition_id = str(role.get("role_definition_id", "")).strip()
    if not role_definition_id:
        return role

    snapshot = RoleSnapshotDefinition(
        role=role,
        definition=get_role_definition(role_definition_id),
        role_definition_id=role_definition_id,
        role_label=str(role.get("id", "")).strip() or role_definition_id,
    )
    _hydrate_role_snapshot_fields(snapshot)
    _hydrate_role_prompt_file(snapshot, hydrated_prompt_files=hydrated_prompt_files)
    return role


def _hydrate_role_snapshot_fields(snapshot: RoleSnapshotDefinition) -> None:
    for field in ("archetype", "prompt_ref", *STRATEGY_ROLE_EXECUTION_FIELDS):
        _hydrate_role_snapshot_field(snapshot, field=field)
    if "name" not in snapshot.role:
        snapshot.role["name"] = snapshot.definition.get("name", "")
    for field in STRATEGY_ROLE_POSTURE_FIELDS:
        if field not in snapshot.role:
            snapshot.role[field] = snapshot.definition.get(field, "")


def _hydrate_role_snapshot_field(snapshot: RoleSnapshotDefinition, *, field: str) -> None:
    if field in snapshot.role:
        provided_value = _canonical_role_snapshot_field(field, snapshot.role.get(field))
        expected_value = _canonical_role_snapshot_field(field, snapshot.definition.get(field))
        if provided_value != expected_value:
            raise StrategySourceError(
                f"workflow role {snapshot.role_label} conflicts with role_definition_id "
                f"{snapshot.role_definition_id} on {field}"
            )
    if field not in snapshot.role:
        snapshot.role[field] = snapshot.definition.get(field, "")


def _hydrate_role_prompt_file(
    snapshot: RoleSnapshotDefinition,
    *,
    hydrated_prompt_files: dict[str, str],
) -> None:
    prompt_ref = str(snapshot.role.get("prompt_ref", "")).strip()
    if not prompt_ref:
        return
    prompt_markdown = str(snapshot.definition.get("prompt_markdown", ""))
    if prompt_ref not in hydrated_prompt_files:
        if prompt_markdown:
            hydrated_prompt_files[prompt_ref] = prompt_markdown
        return
    provided_prompt_markdown = hydrated_prompt_files[prompt_ref]
    if prompt_markdown and _canonical_prompt_markdown(provided_prompt_markdown) != _canonical_prompt_markdown(prompt_markdown):
        raise StrategySourceError(
            f"workflow role {snapshot.role_label} conflicts with role_definition_id "
            f"{snapshot.role_definition_id} on prompt_markdown"
        )


def _canonical_role_snapshot_field(field: str, value: object) -> object:
    if field == "archetype":
        return normalize_strategy_archetype(str(value or ""))
    if field == "prompt_ref":
        raw_prompt_ref = str(value or "").strip()
        return normalize_strategy_prompt_ref(raw_prompt_ref) if raw_prompt_ref else ""
    if field == "command_args_text":
        return str(value or "")
    return str(value or "").strip()


def _canonical_prompt_markdown(markdown: object) -> str:
    return str(markdown or "").replace("\r\n", "\n").replace("\r", "\n").strip()
