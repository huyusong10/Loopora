from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

from loopora.agent_adapter_claude_hook import (
    CLAUDE_SESSION_HOOK_COMMAND,
    CLAUDE_SESSION_HOOK_GROUP,
    CLAUDE_SESSION_HOOK_RELATIVE_PATH,
    CLAUDE_SESSION_HOOK_SETTINGS_REF,
    CLAUDE_SETTINGS_RELATIVE_PATH,
    claude_session_additional_context as claude_session_additional_context,
    claude_session_hook_script as claude_session_hook_script,
)
from loopora.service_types import LooporaConflictError, LooporaError


def assert_host_config_is_replaceable(kind: str, root: Path) -> None:
    if kind != "claude":
        return
    settings_path = root / CLAUDE_SETTINGS_RELATIVE_PATH
    if not settings_path.exists():
        return
    _assert_claude_settings_can_merge_loopora_hook(_read_json_object(settings_path, label="Claude Code settings"))


def install_host_config(kind: str, root: Path) -> None:
    if kind == "claude":
        _install_claude_session_hook(root)


def uninstall_host_config(kind: str, root: Path) -> list[str]:
    if kind != "claude":
        return []
    return _uninstall_claude_session_hook(root)


def preview_uninstall_host_config(kind: str, root: Path) -> list[str]:
    if kind != "claude":
        return []
    return _preview_uninstall_claude_session_hook(root)


def host_config_status(kind: str, root: Path, *, manifest_exists: bool) -> dict[str, Any] | None:
    if kind != "claude":
        return None
    payload: dict[str, Any] = {
        "path": CLAUDE_SESSION_HOOK_SETTINGS_REF,
        "exists": (root / CLAUDE_SETTINGS_RELATIVE_PATH).exists(),
        "expected_sha256": "",
        "actual_sha256": "",
        "state": "missing",
    }
    try:
        settings = _read_claude_settings(root)
    except LooporaError as exc:
        payload["state"] = "error"
        payload["error"] = str(exc)
        return {
            "payload": payload,
            "needs_update": False,
            "unmanaged_conflict": manifest_exists,
        }
    try:
        _assert_claude_settings_can_merge_loopora_hook(settings)
    except LooporaError as exc:
        payload["state"] = "error"
        payload["error"] = str(exc)
        return {
            "payload": payload,
            "needs_update": False,
            "unmanaged_conflict": manifest_exists,
        }
    if _claude_settings_has_loopora_session_hook(settings):
        payload["state"] = "current"
        return {
            "payload": payload,
            "needs_update": False,
            "unmanaged_conflict": False,
        }
    return {
        "payload": payload,
        "needs_update": manifest_exists,
        "unmanaged_conflict": False,
    }


def claude_session_hook_check_passes(root: Path) -> bool:
    hook_text = _read_text_or_empty(root / CLAUDE_SESSION_HOOK_RELATIVE_PATH)
    try:
        settings = _read_claude_settings(root)
    except LooporaError:
        return False
    return "CLAUDE_SESSION_ID" in hook_text and _claude_settings_has_loopora_session_hook(settings)


def _install_claude_session_hook(root: Path) -> None:
    settings = _read_claude_settings(root)
    updated = _remove_claude_session_hook(settings)
    hooks = updated.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise LooporaConflictError("refusing to update Claude Code settings because hooks is not an object")
    session_start = hooks.setdefault("SessionStart", [])
    if not isinstance(session_start, list):
        raise LooporaConflictError("refusing to update Claude Code settings because hooks.SessionStart is not a list")
    session_start.append(json.loads(json.dumps(CLAUDE_SESSION_HOOK_GROUP)))
    _write_claude_settings(root, updated)


def _uninstall_claude_session_hook(root: Path) -> list[str]:
    settings_path = root / CLAUDE_SETTINGS_RELATIVE_PATH
    if not settings_path.exists():
        return []
    settings = _read_claude_settings(root)
    updated = _remove_claude_session_hook(settings)
    if updated == settings:
        return []
    if updated:
        _write_claude_settings(root, updated)
    else:
        settings_path.unlink()
        _remove_empty_parents(root, settings_path.parent)
    return [CLAUDE_SESSION_HOOK_SETTINGS_REF]


def _preview_uninstall_claude_session_hook(root: Path) -> list[str]:
    settings_path = root / CLAUDE_SETTINGS_RELATIVE_PATH
    if not settings_path.exists():
        return []
    settings = _read_claude_settings(root)
    updated = _remove_claude_session_hook(settings)
    if updated == settings:
        return []
    return [CLAUDE_SESSION_HOOK_SETTINGS_REF]


def _read_claude_settings(root: Path) -> dict[str, Any]:
    settings_path = root / CLAUDE_SETTINGS_RELATIVE_PATH
    if not settings_path.exists():
        return {}
    return _read_json_object(settings_path, label="Claude Code settings")


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise LooporaConflictError(f"{label} could not be read: {CLAUDE_SETTINGS_RELATIVE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise LooporaConflictError(f"{label} must be valid JSON: {CLAUDE_SETTINGS_RELATIVE_PATH}") from exc
    if not isinstance(payload, dict):
        raise LooporaConflictError(f"{label} must be a JSON object: {CLAUDE_SETTINGS_RELATIVE_PATH}")
    return payload


def _assert_claude_settings_can_merge_loopora_hook(settings: dict[str, Any]) -> None:
    hooks = settings.get("hooks")
    if hooks is not None and not isinstance(hooks, dict):
        raise LooporaConflictError("refusing to update Claude Code settings because hooks is not an object")
    if isinstance(hooks, dict):
        session_start = hooks.get("SessionStart")
        if session_start is not None and not isinstance(session_start, list):
            raise LooporaConflictError("refusing to update Claude Code settings because hooks.SessionStart is not a list")


def _write_claude_settings(root: Path, payload: dict[str, Any]) -> None:
    settings_path = root / CLAUDE_SETTINGS_RELATIVE_PATH
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(settings_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _remove_claude_session_hook(settings: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(settings))
    hooks = updated.get("hooks")
    if not isinstance(hooks, dict):
        return updated
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return updated

    cleaned_groups: list[Any] = []
    for group in session_start:
        if not isinstance(group, dict):
            cleaned_groups.append(group)
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            cleaned_groups.append(group)
            continue
        cleaned_handlers = [
            handler
            for handler in handlers
            if not (isinstance(handler, dict) and str(handler.get("command") or "").strip() == CLAUDE_SESSION_HOOK_COMMAND)
        ]
        if cleaned_handlers:
            cleaned_group = dict(group)
            cleaned_group["hooks"] = cleaned_handlers
            cleaned_groups.append(cleaned_group)

    if cleaned_groups:
        hooks["SessionStart"] = cleaned_groups
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        updated.pop("hooks", None)
    return updated


def _claude_settings_has_loopora_session_hook(settings: dict[str, Any]) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return False
    for group in session_start:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if isinstance(handler, dict) and str(handler.get("command") or "").strip() == CLAUDE_SESSION_HOOK_COMMAND:
                return True
    return False


def _read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        with suppress(OSError):
            tmp.unlink()
        raise


def _remove_empty_parents(root: Path, directory: Path) -> None:
    current = directory
    while current != root and root in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
