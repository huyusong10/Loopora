from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_command_prefix import copyable_loopora_command

RECOVERY_CLI_SUMMARY_SCHEMA_VERSION = 1
RECOVERY_PURPOSE_SELECTION_GROUP = "recovery_purpose"


def recovery_create_json_payload(result: Mapping[str, object]) -> dict[str, object]:
    actions = recovery_create_next_actions(result)
    payload: dict[str, object] = {
        "recovery_create_summary": {
            "schema_version": RECOVERY_CLI_SUMMARY_SCHEMA_VERSION,
            "state": "archive_created",
            "file_count": int(result.get("file_count") or 0),
            "public_safe": False,
        },
        **dict(result),
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="recovery_create_summary")


def recovery_inspect_json_payload(result: Mapping[str, object]) -> dict[str, object]:
    actions = recovery_inspect_next_actions(result)
    payload: dict[str, object] = {
        "recovery_inspect_summary": {
            "schema_version": RECOVERY_CLI_SUMMARY_SCHEMA_VERSION,
            "state": "archive_valid",
            "file_count": int(result.get("file_count") or 0),
            "public_safe": False,
            "recovery_purpose_selection_required": True,
            "recovery_choice_kinds": [str(action["kind"]) for action in actions],
        },
        **dict(result),
        "recovery_purpose_selection_required": True,
        "recovery_choice_kinds": [str(action["kind"]) for action in actions],
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="recovery_inspect_summary")


def recovery_restore_json_payload(result: Mapping[str, object]) -> dict[str, object]:
    state = recovery_restore_state(result)
    actions = recovery_restore_next_actions(result)
    payload: dict[str, object] = {
        "recovery_restore_summary": {
            "schema_version": RECOVERY_CLI_SUMMARY_SCHEMA_VERSION,
            "state": state,
            "dry_run": result.get("dry_run") is not False,
            "planned_count": len(list(result.get("planned") or [])),
            "already_present_count": len(list(result.get("already_present") or [])),
            "conflict_count": len(list(result.get("conflicts") or [])),
            "restored_count": len(list(result.get("restored") or [])),
            "public_safe": False,
        },
        **dict(result),
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="recovery_restore_summary")


def recovery_create_next_actions(result: Mapping[str, object]) -> list[dict[str, object]]:
    path = _value(result, "path")
    if not path:
        return []
    return [
        {
            "kind": "inspect_recovery_archive",
            "command": copyable_loopora_command(f"loopora recovery inspect {shlex.quote(path)}"),
            "private_content": True,
            "public_safe": False,
        }
    ]


def recovery_inspect_next_actions(result: Mapping[str, object]) -> list[dict[str, object]]:
    source = result.get("source") if isinstance(result.get("source"), Mapping) else {}
    workdir = _value(source, "workdir")
    path = _value(result, "path")
    if not workdir or not path:
        return []
    common = {
        "choice_group": RECOVERY_PURPOSE_SELECTION_GROUP,
        "selection_required": True,
        "mutually_exclusive": True,
        "destructive": False,
        "public_safe": False,
    }
    return [
        {
            **common,
            "kind": "preview_app_database_reset",
            "purpose": "continue_app_state_recovery",
            "command": copyable_loopora_command(
                f"loopora dev reset --scope app --workdir {shlex.quote(workdir)}"
            ),
        },
        {
            **common,
            "kind": "preview_exact_path_restore",
            "purpose": "recover_missing_files",
            "command": _restore_command(path=path, workdir=workdir),
        },
        {
            **common,
            "kind": "confirm_readiness",
            "purpose": "no_recovery_write",
            "command": _doctor_command(workdir),
        },
    ]


def recovery_restore_next_actions(result: Mapping[str, object]) -> list[dict[str, object]]:
    state = recovery_restore_state(result)
    path = _value(result, "archive")
    workdir = _value(result, "workdir")
    if state == "restore_blocked":
        return [
            {"kind": "resolve_restore_conflicts", "destructive": False, "public_safe": False},
            {
                "kind": "retry_restore_preview",
                "command": _restore_command(path=path, workdir=workdir),
                "after_action": "resolve_restore_conflicts",
                "destructive": False,
                "public_safe": False,
            },
        ]
    if state == "restore_preview":
        return [
            {"kind": "review_restore_scope", "destructive": False, "public_safe": False},
            {
                "kind": "apply_recovery_restore",
                "command": f"{_restore_command(path=path, workdir=workdir)} --yes",
                "after_action": "review_restore_scope",
                "destructive": True,
                "public_safe": False,
            },
        ]
    if not workdir:
        return []
    kind = "confirm_readiness" if state == "restore_complete" else "confirm_readiness_if_needed"
    return [
        {
            "kind": kind,
            "command": _doctor_command(workdir),
            "destructive": False,
            "public_safe": False,
        }
    ]


def recovery_restore_state(result: Mapping[str, object]) -> str:
    if str(result.get("status") or "") == "blocked":
        return "restore_blocked"
    if str(result.get("status") or "") == "restored":
        return "restore_complete"
    if list(result.get("planned") or []):
        return "restore_preview"
    return "no_restore_needed"


def _restore_command(*, path: str, workdir: str) -> str:
    if not path or not workdir:
        return ""
    return copyable_loopora_command(
        f"loopora recovery restore {shlex.quote(path)} --workdir {shlex.quote(workdir)}"
    )


def _doctor_command(workdir: str) -> str:
    return copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(workdir)}")


def _value(source: Mapping[str, object], key: str) -> str:
    return str(source.get(key) or "").strip()


__all__ = (
    "RECOVERY_CLI_SUMMARY_SCHEMA_VERSION",
    "recovery_create_json_payload",
    "recovery_create_next_actions",
    "recovery_inspect_json_payload",
    "recovery_inspect_next_actions",
    "recovery_restore_json_payload",
    "recovery_restore_next_actions",
    "recovery_restore_state",
)
