from __future__ import annotations

import shlex
from collections.abc import Iterable, Mapping

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_resource_recovery import project_resource_recovery_action_contract
from loopora.cli_shared import strategy_source_bundle_from_entity

DELETE_SCOPE_REVIEW_NOTE = "Run this only after reviewing the dry-run scope."


def bundle_list_rows(bundles: Iterable[Mapping[str, object]]) -> list[str]:
    return [
        f"{item['id']}  {item['name']}  revision={item.get('revision', 1)}  loop={item.get('loop_id', '-') or '-'}  workdir={item.get('workdir', '-') or '-'}"
        for item in bundles
    ]


def role_definition_list_rows(definitions: Iterable[Mapping[str, object]]) -> list[str]:
    return [
        f"{item['id']}  {item['name']}  source={item.get('source', 'custom')}  "
        f"archetype={item.get('archetype', 'builder')}  executor={item.get('executor_kind', 'codex')}"
        for item in definitions
    ]


def orchestration_list_rows(orchestrations: Iterable[Mapping[str, object]]) -> list[str]:
    rows: list[str] = []
    for item in orchestrations:
        strategy_source = strategy_source_bundle_from_entity(item)[0] or {}
        rows.append(
            f"{item['id']}  {item['name']}  "
            f"source={item.get('source', 'custom')}  "
            f"roles={len(strategy_source.get('roles', []))}  "
            f"steps={len(strategy_source.get('steps', []))}"
        )
    return rows


def project_bundle_delete_preview(preview: Mapping[str, object], bundle_id: str) -> dict[str, object]:
    return _project_delete_preview(
        preview,
        resource_id=bundle_id,
        delete_allowed=preview.get("delete_allowed") is True,
        action_kind="delete_bundle",
        command_prefix="loopora bundles delete",
    )


def project_role_definition_delete_preview(preview: Mapping[str, object], role_definition_id: str) -> dict[str, object]:
    return _project_delete_preview(
        preview,
        resource_id=role_definition_id,
        delete_allowed=preview.get("delete_allowed") is True,
        action_kind="delete_role_definition",
        command_prefix="loopora roles delete",
    )


def project_orchestration_delete_preview(preview: Mapping[str, object], orchestration_id: str) -> dict[str, object]:
    return _project_delete_preview(
        preview,
        resource_id=orchestration_id,
        delete_allowed=preview.get("delete_allowed") is True,
        action_kind="delete_orchestration",
        command_prefix="loopora orchestrations delete",
    )


def _project_delete_preview(
    preview: Mapping[str, object],
    *,
    resource_id: str,
    delete_allowed: bool,
    action_kind: str,
    command_prefix: str,
) -> dict[str, object]:
    payload = dict(preview)
    payload["next_actions"] = _delete_next_actions(
        resource_id,
        delete_allowed=delete_allowed,
        action_kind=action_kind,
        command_prefix=command_prefix,
    )
    return project_resource_recovery_action_contract(payload)


def _delete_next_actions(
    resource_id: str,
    *,
    delete_allowed: bool,
    action_kind: str,
    command_prefix: str,
) -> list[dict[str, str]]:
    if not delete_allowed:
        return []
    return [
        {
            "kind": action_kind,
            "command": copyable_loopora_command(f"{command_prefix} {shlex.quote(resource_id)}"),
            "note": DELETE_SCOPE_REVIEW_NOTE,
        }
    ]
