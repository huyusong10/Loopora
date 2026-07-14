from __future__ import annotations

import json
from pathlib import Path
import shlex
from typing import Any

import loopora.agent_adapter_static_checks as _agent_adapter_static_checks
from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_adapter_check_recovery import adapter_check_recovery as _adapter_check_recovery
from loopora.agent_adapter_check_utils import (
    adapter_label as _adapter_label,
    adapter_unavailable_summary as _adapter_unavailable_summary,
    read_text_or_empty as _read_text_or_empty,
)
from loopora.agent_adapter_context_binding import resolve_adapter_project_root
from loopora.agent_adapter_host_config import (
    assert_host_config_is_replaceable as _assert_host_config_is_replaceable,
    install_host_config as _install_host_config,
    preview_uninstall_host_config as _preview_uninstall_host_config,
    uninstall_host_config as _uninstall_host_config,
)
from loopora.agent_adapter_managed_files import (
    assert_targets_are_replaceable as _assert_targets_are_replaceable,
    atomic_write_text as _atomic_write_text,
    remove_empty_parents as _remove_empty_parents,
    remove_obsolete_managed_files as _remove_obsolete_managed_files,
    sha256_text as _sha256_text,
)
from loopora.agent_adapter_manifest import (
    managed_marker as _managed_marker,
    manifest_hash_for_path as _manifest_hash_for_path,
    manifest_paths as _manifest_paths,
    manifest_payload as _manifest_payload,
    manifest_relative_path as _manifest_relative_path,
    read_manifest as _read_manifest,
)
from loopora.agent_adapter_status import (
    managed_adapter_status as _managed_adapter_status,
    not_implemented_adapter_status as _not_implemented_status,
)
from loopora.agent_adapter_templates import managed_templates as _adapter_managed_templates
from loopora.agent_native_adapter_contracts import (
    AGENT_ADAPTER_KINDS,
    normalize_agent_adapter_kind,
)
from loopora.settings import remember_recent_workdir
from loopora.service_types import LooporaError

IMPLEMENTED_AGENT_ADAPTERS = {"codex", "claude", "opencode"}
REMOVE_FAILED_REASON = "remove_failed"
FIRST_TASK_MESSAGE_EXAMPLE = (
    "/loopora-plan\n\nLoopora fit: multi-round evidence review is needed for permission, replay, "
    "error, and rollback proof; Goal: ship a support-ops incident dashboard that preserves audit trails; "
    "Fake-done risks: happy-path UI with no replay/error proof, missing permission checks, or unclear rollback; "
    "Required evidence: project tests, one browser journey, and a GateKeeper-readable evidence summary; "
    "Judgment tradeoffs: keep scope narrow, fail closed on unproven data safety."
)
FIRST_TASK_HANDOFF_POLICY = {
    "preferred_source": "completed_fit_review",
    "fallback_source": "generic_example",
    "fit_command": "loopora fit",
    "plan_command": "/loopora-plan",
    "copy_rule": (
        "If you completed loopora fit with task review, paste its copyable /loopora-plan handoff as one Agent message; "
        "otherwise use the generic orientation example only as a review starting point."
    ),
}
FIRST_TASK_MESSAGE_EXAMPLE_STATE = {
    "kind": "generic_orientation_example",
    "source": "generic_example",
    "copy_allowed": False,
    "completed_review": False,
}
_adapter_static_checks = _agent_adapter_static_checks.adapter_static_checks
_adapter_install_next_steps = _agent_adapter_static_checks.adapter_install_next_steps
_adapter_install_next_commands = _agent_adapter_static_checks.adapter_install_next_commands
_adapter_uninstall_next_actions = _agent_adapter_static_checks.adapter_uninstall_next_actions
_adapter_uninstall_next_commands = _agent_adapter_static_checks.adapter_uninstall_next_commands
_adapter_uninstall_next_steps = _agent_adapter_static_checks.adapter_uninstall_next_steps
_adapter_native_surface = _agent_adapter_static_checks.adapter_native_surface


def list_agent_adapter_statuses(workdir: Path | str | None) -> list[dict[str, Any]]:
    root = resolve_adapter_project_root(workdir)
    return [agent_adapter_status(kind, root) for kind in AGENT_ADAPTER_KINDS]


def agent_adapter_status(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        return _not_implemented_status(kind, root)
    return _status_with_handoff(kind, root, _managed_adapter_status(kind, root))


def _status_with_handoff(kind: str, root: Path, status: dict[str, Any]) -> dict[str, Any]:
    if status.get("status") not in {"installed", "needs_update"}:
        return status
    return {
        **status,
        "next_commands": _adapter_install_next_commands(kind, root),
        "first_task_message_example": adapter_first_task_message_example(),
        "first_task_message_example_state": adapter_first_task_message_example_state(),
        "first_task_handoff_policy": adapter_first_task_handoff_policy(workdir=root),
    }


def check_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    status = agent_adapter_status(kind, root)
    checks = _adapter_static_checks(kind, root, status) if kind in IMPLEMENTED_AGENT_ADAPTERS else []
    failed = [item for item in checks if item.get("status") != "pass"]
    check_status = "pass" if not failed and status.get("status") == "installed" else "fail"
    result = {
        **status,
        "check_status": check_status,
        "check_recovery": _adapter_check_recovery(kind, root, status=status, check_status=check_status),
        "checks": checks,
        "native_surface": _adapter_native_surface(kind, root),
    }
    if check_status == "pass":
        result["next_steps"] = _adapter_install_next_steps(kind, root)
        result["next_commands"] = _adapter_install_next_commands(kind, root)
        result["first_task_message_example"] = adapter_first_task_message_example()
        result["first_task_message_example_state"] = adapter_first_task_message_example_state()
        result["first_task_handoff_policy"] = adapter_first_task_handoff_policy(workdir=root)
    return result


def install_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        raise LooporaError(_adapter_unavailable_summary(kind))
    templates = _managed_templates(kind)
    marker = _managed_marker(kind)
    _assert_targets_are_replaceable(kind, root, templates)
    _assert_host_config_is_replaceable(kind, root)
    removed_obsolete_files = _remove_obsolete_managed_files(kind, root, templates)
    written: list[dict[str, str]] = []
    for relative_path, content in templates.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        current = _read_text_or_empty(target)
        if current != content:
            _atomic_write_text(target, content)
        written.append(
            {
                "path": relative_path,
                "sha256": _sha256_text(content),
            }
        )
    _install_host_config(kind, root)
    manifest = _manifest_payload(kind, root, written)
    manifest_path = root / _manifest_relative_path(kind)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing_manifest, _ = _read_manifest(kind, root)
    if existing_manifest != manifest:
        _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    remember_recent_workdir(root)
    status = _managed_adapter_status(kind, root)
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "status": status["status"],
        "next_steps": _adapter_install_next_steps(kind, root),
        "next_commands": _adapter_install_next_commands(kind, root),
        "first_task_message_example": adapter_first_task_message_example(),
        "first_task_message_example_state": adapter_first_task_message_example_state(),
        "first_task_handoff_policy": adapter_first_task_handoff_policy(workdir=root),
        "native_surface": _adapter_native_surface(kind, root),
        "manifest_path": str(manifest_path),
        "managed_files": status["managed_files"],
        "managed_marker": marker,
        "removed_obsolete_files": removed_obsolete_files,
    }


def uninstall_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        raise LooporaError(_adapter_unavailable_summary(kind))

    plan = _agent_adapter_uninstall_plan(kind, root)
    removed: list[str] = []
    kept = list(plan["kept_files"])
    for relative_path in plan["managed_files_to_remove"]:
        target = root / relative_path
        if not target.exists():
            continue
        try:
            target.unlink()
        except OSError:
            kept.append({"path": relative_path, "reason": REMOVE_FAILED_REASON})
            continue
        removed.append(relative_path)
        _remove_empty_parents(root, target.parent)

    removed.extend(_uninstall_host_config(kind, root))

    manifest_path = root / _manifest_relative_path(kind)
    if manifest_path.exists():
        try:
            manifest_path.unlink()
            _remove_empty_parents(root, manifest_path.parent)
        except OSError:
            kept.append({"path": _manifest_relative_path(kind), "reason": REMOVE_FAILED_REASON})

    return _agent_adapter_uninstall_result(
        kind,
        root,
        {
            "status": _managed_adapter_status(kind, root)["status"],
            "dry_run": False,
            "removed_files": removed,
            "kept_files": kept,
            "manifest_error": str(plan["manifest_error"]),
        },
    )


def preview_agent_adapter_uninstall(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        raise LooporaError(_adapter_unavailable_summary(kind))

    plan = _agent_adapter_uninstall_plan(kind, root)
    planned_files = list(plan["managed_files_to_remove"]) + list(plan["host_config_files_to_remove"])
    kept = list(plan["kept_files"])
    return _agent_adapter_uninstall_result(
        kind,
        root,
        {
            "delete_allowed": True,
            "would_delete": {
                "adapter": kind,
                "removed_file_count": len(planned_files),
                "kept_file_count": len(kept),
            },
            "status": "dry_run",
            "dry_run": True,
            "removed_files": planned_files,
            "kept_files": kept,
            "manifest_error": str(plan["manifest_error"]),
        },
    )


def _agent_adapter_uninstall_plan(kind: str, root: Path) -> dict[str, Any]:
    templates = _managed_templates(kind)
    marker = _managed_marker(kind)
    manifest_payload, manifest_error = _read_manifest(kind, root)
    manifest_paths = _manifest_paths(manifest_payload) if isinstance(manifest_payload, dict) else []
    managed_paths = sorted(set(manifest_paths) | set(templates))

    removable: list[str] = []
    kept: list[dict[str, str]] = []
    for relative_path in managed_paths:
        target = root / relative_path
        if not target.exists():
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            kept.append({"path": relative_path, "reason": "unreadable"})
            continue
        manifest_hash = _manifest_hash_for_path(manifest_payload, relative_path) if isinstance(manifest_payload, dict) else ""
        template_hash = _sha256_text(templates.get(relative_path, ""))
        content_hash = _sha256_text(content)
        if marker in content or content_hash in {manifest_hash, template_hash}:
            removable.append(relative_path)
        else:
            kept.append({"path": relative_path, "reason": "not_loopora_managed"})

    host_config_files = _preview_uninstall_host_config(kind, root)
    return {
        "managed_files_to_remove": removable,
        "host_config_files_to_remove": host_config_files,
        "kept_files": kept,
        "manifest_error": manifest_error,
    }


def _agent_adapter_uninstall_result(
    kind: str,
    root: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    kept_files = [item for item in list(result.get("kept_files") or []) if isinstance(item, dict)]
    return project_next_action_readiness_contract({
        **result,
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "status": str(result.get("status") or ""),
        "dry_run": result.get("dry_run") is True,
        "kept_files": kept_files,
        "next_steps": _adapter_uninstall_next_steps(kind, root, has_kept_files=bool(kept_files)),
        "next_commands": _adapter_uninstall_next_commands(kind, root),
        "next_actions": _adapter_uninstall_next_actions(kind, root, has_kept_files=bool(kept_files)),
        "manifest_error": str(result.get("manifest_error") or ""),
    })


def adapter_first_task_message_example() -> str:
    return FIRST_TASK_MESSAGE_EXAMPLE


def adapter_first_task_message_example_state() -> dict[str, object]:
    return dict(FIRST_TASK_MESSAGE_EXAMPLE_STATE)


def adapter_first_task_handoff_policy(
    *,
    workdir: Path | str | None = None,
    fit_command: str = "",
) -> dict[str, str]:
    policy = dict(FIRST_TASK_HANDOFF_POLICY)
    command = _adapter_first_task_fit_command(workdir=workdir, fit_command=fit_command)
    policy["fit_command"] = command
    policy["copy_rule"] = str(policy.get("copy_rule") or "").replace(
        FIRST_TASK_HANDOFF_POLICY["fit_command"],
        command,
    )
    return policy


def _adapter_first_task_fit_command(*, workdir: Path | str | None, fit_command: str) -> str:
    command = str(fit_command or "").strip()
    if command:
        return command
    if workdir is None:
        return FIRST_TASK_HANDOFF_POLICY["fit_command"]
    root = _handoff_workdir_path(workdir)
    return f"{FIRST_TASK_HANDOFF_POLICY['fit_command']} --workdir {shlex.quote(str(root))}"


def _handoff_workdir_path(workdir: Path | str) -> Path:
    candidate = Path(workdir).expanduser()
    try:
        return candidate.resolve()
    except OSError:
        return candidate if candidate.is_absolute() else Path.cwd() / candidate


def _managed_templates(kind: str) -> dict[str, str]:
    return _adapter_managed_templates(kind)
