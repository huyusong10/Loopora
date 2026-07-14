from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.web_home_attention import home_loop_sections

EXISTING_WORK_STATUS_SCHEMA_VERSION = 2


def existing_work_status_payload(
    service,
    *,
    workdir: Path | None,
    all_projects: bool,
    language: str,
    reconcile_runtime_state: bool = False,
) -> dict[str, object]:
    scope_workdir = "" if all_projects else str(workdir or "")
    runtime_reconciliation = _runtime_reconciliation_state(
        service,
        workdir=scope_workdir,
        apply=reconcile_runtime_state,
    )
    sections = (
        home_loop_sections(
            service,
            workdir_context=scope_workdir,
            reconcile_orphans=False,
        )
        if service is not None
        else {"active_loops": [], "recent_loops": [], "loops": []}
    )
    attention = [_status_item(item, language=language, category="attention") for item in sections["active_loops"]]
    recent = [_status_item(item, language=language, category="recent") for item in sections["recent_loops"]]
    saved_not_run = [
        _status_item(item, language=language, category="saved_not_run")
        for item in sections["loops"]
        if not str(item.get("latest_run_id") or "").strip()
    ]
    primary = next(iter([*attention, *recent, *saved_not_run]), None)
    state = "needs_attention" if attention else ("recent" if recent else ("saved_not_run" if saved_not_run else "empty"))
    next_actions = list(primary.get("next_actions") or []) if primary else _empty_status_actions(scope_workdir)
    if runtime_reconciliation["status"] == "required":
        next_actions.insert(0, _runtime_reconciliation_action(scope_workdir, all_projects=all_projects))
    return {
        "schema_version": EXISTING_WORK_STATUS_SCHEMA_VERSION,
        "status": state,
        "read_only": not runtime_reconciliation["changed"],
        "reconcile_requested": reconcile_runtime_state,
        "scope": "all_projects" if all_projects else "target_project",
        "workdir": scope_workdir,
        "language": language,
        "command_fields_are_local_only": True,
        "command_fields_public_pasteable": False,
        "counts": {
            "needs_attention": len(attention),
            "recent": len(recent),
            "saved_not_run": len(saved_not_run),
            "saved_loops": len(sections["loops"]),
        },
        "runtime_reconciliation": runtime_reconciliation,
        "primary_item": primary,
        "attention": attention,
        "recent": recent,
        "saved_not_run": saved_not_run,
        "next_actions": next_actions,
    }


def _runtime_reconciliation_state(service, *, workdir: str, apply: bool) -> dict[str, object]:
    preview_command = getattr(service, "runtime_reconciliation_preview", None)
    before = preview_command(workdir=workdir) if callable(preview_command) else {}
    stale_runs = list(before.get("stale_runs") or []) if isinstance(before, dict) else []
    orphaned_sessions = list(before.get("orphaned_planning_sessions") or []) if isinstance(before, dict) else []
    result: dict[str, object] = {}
    if apply:
        reconcile_command = getattr(service, "reconcile_orphaned_runtime_state", None)
        result = reconcile_command(workdir=workdir) if callable(reconcile_command) else {}
    required = bool(stale_runs or orphaned_sessions)
    return {
        "status": "applied" if apply and result.get("changed") else ("required" if required else "not_needed"),
        "required_before": required,
        "changed": bool(result.get("changed")),
        "stale_run_count": len(stale_runs),
        "orphaned_planning_session_count": len(orphaned_sessions),
        "stale_runs": stale_runs,
        "orphaned_planning_sessions": orphaned_sessions,
        "reconciled_run_ids": list(result.get("reconciled_run_ids") or []),
        "reconciled_planning_session_ids": list(result.get("reconciled_planning_session_ids") or []),
    }


def _runtime_reconciliation_action(workdir: str, *, all_projects: bool) -> dict[str, object]:
    scope_args = "--all" if all_projects else f"--workdir {shlex.quote(workdir)}"
    return {
        "kind": "reconcile_orphaned_runtime_state",
        "command": copyable_loopora_command(f"loopora status {scope_args} --reconcile"),
        "changes_runtime_records": True,
        "starts_work": False,
    }


def _status_item(item: Mapping[str, object], *, language: str, category: str) -> dict[str, object]:
    source_kind = str(item.get("source_kind") or "loop")
    item_id = str(item.get("id") or "")
    workdir = str(item.get("workdir") or "")
    status_label = str(item.get("status_label") or item.get("latest_status") or "draft")
    reason = _localized(item, "attention_reason", language)
    action = _localized(item, "attention_action", language)
    hint = _localized(item, "card_hint", language)
    excerpt = _localized(item, "card_excerpt", language)
    web_path = str(item.get("card_href") or "")
    next_actions = _item_next_actions(workdir=workdir, web_path=web_path, item_id=item_id, source_kind=source_kind)
    return {
        "id": item_id,
        "source_kind": source_kind,
        "category": category,
        "name": str(item.get("name") or item.get("title") or item_id),
        "workdir": workdir,
        "status": status_label,
        "latest_run_id": str(item.get("latest_run_id") or ""),
        "reason_kind": str(item.get("attention_reason_kind") or ""),
        "reason": reason,
        "action_kind": str(item.get("attention_action_kind") or ""),
        "action": action,
        "summary": hint,
        "excerpt": excerpt,
        "updated_at": str(item.get("updated_at") or ""),
        "created_at": str(item.get("created_at") or ""),
        "web_path": web_path,
        "next_actions": next_actions,
    }


def _localized(item: Mapping[str, object], field: str, language: str) -> str:
    localized = str(item.get(f"{field}_{language}") or "").strip()
    return localized or str(item.get(field) or "").strip()


def _item_next_actions(*, workdir: str, web_path: str, item_id: str, source_kind: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if workdir and web_path:
        command = " ".join(
            [
                "loopora serve --open --workdir",
                shlex.quote(workdir),
                "--open-path",
                shlex.quote(web_path),
            ]
        )
        actions.append({"kind": "open_existing_work", "command": copyable_loopora_command(command)})
    if source_kind == "loop" and item_id:
        command = copyable_loopora_command(f"loopora loops status {shlex.quote(item_id)}")
        actions.append({"kind": "inspect_loop_status", "command": command})
    return actions


def _empty_status_actions(workdir: str) -> list[dict[str, str]]:
    workdir_arg = shlex.quote(workdir) if workdir else '"$PWD"'
    return [
        {
            "kind": "start_new_work",
            "command": copyable_loopora_command(f"loopora start --workdir {workdir_arg}"),
        }
    ]


__all__ = ["EXISTING_WORK_STATUS_SCHEMA_VERSION", "existing_work_status_payload"]
