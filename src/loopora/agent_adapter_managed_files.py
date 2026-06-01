from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_manifest import (
    CLAUDE_MANIFEST_RELATIVE_PATH,
    CODEX_MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATHS,
    OBSOLETE_MANAGED_PATHS,
    OPENCODE_MANIFEST_RELATIVE_PATH,
    managed_marker,
    manifest_hash_for_path,
    manifest_paths,
    manifest_payload,
    manifest_relative_path,
    obsolete_managed_paths,
    read_manifest,
)
from loopora.service_types import LooporaConflictError

__all__ = [
    "CLAUDE_MANIFEST_RELATIVE_PATH",
    "CODEX_MANIFEST_RELATIVE_PATH",
    "MANIFEST_RELATIVE_PATH",
    "MANIFEST_RELATIVE_PATHS",
    "OBSOLETE_MANAGED_PATHS",
    "OPENCODE_MANIFEST_RELATIVE_PATH",
    "assert_targets_are_replaceable",
    "atomic_write_text",
    "managed_file_status",
    "managed_marker",
    "managed_status_paths",
    "manifest_hash_for_path",
    "manifest_paths",
    "manifest_payload",
    "manifest_relative_path",
    "obsolete_managed_paths",
    "read_manifest",
    "remove_empty_parents",
    "remove_obsolete_managed_files",
    "sha256_text",
]


def managed_file_status(
    kind: str,
    root: Path,
    relative_path: str,
    expected: str,
    *,
    manifest_context: tuple[dict[str, Any] | None, bool],
) -> dict[str, Any]:
    manifest_payload, manifest_exists = manifest_context
    target = root / relative_path
    expected_hash = sha256_text(expected) if expected else ""
    payload: dict[str, Any] = {
        "path": relative_path,
        "exists": target.exists(),
        "expected_sha256": expected_hash,
        "actual_sha256": "",
        "state": "missing",
    }
    if not target.exists():
        return {
            "payload": payload,
            "current": False,
            "needs_update": manifest_exists,
            "managed_marker": False,
            "unmanaged_conflict": False,
        }

    try:
        content = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        payload["state"] = "error"
        payload["error"] = str(exc)
        return {
            "payload": payload,
            "current": False,
            "needs_update": False,
            "managed_marker": False,
            "unmanaged_conflict": True,
        }

    actual_hash = sha256_text(content)
    marker = managed_marker(kind)
    payload["actual_sha256"] = actual_hash
    if expected and actual_hash == expected_hash:
        payload["state"] = "current"
        return {
            "payload": payload,
            "current": True,
            "needs_update": False,
            "managed_marker": marker in content,
            "unmanaged_conflict": False,
        }
    manifest_hash = manifest_hash_for_path(manifest_payload, relative_path) if manifest_exists else ""
    if marker in content or (manifest_hash and actual_hash == manifest_hash):
        payload["state"] = "needs_update"
        return {
            "payload": payload,
            "current": False,
            "needs_update": True,
            "managed_marker": marker in content,
            "unmanaged_conflict": False,
        }
    payload["state"] = "unmanaged_conflict"
    return {
        "payload": payload,
        "current": False,
        "needs_update": False,
        "managed_marker": False,
        "unmanaged_conflict": True,
    }


def managed_status_paths(
    kind: str,
    root: Path,
    manifest_payload: dict[str, Any] | None,
    *,
    manifest_exists: bool,
    templates: dict[str, str],
) -> list[str]:
    paths = set(templates)
    if manifest_exists:
        paths.update(manifest_paths(manifest_payload))
    for relative_path in obsolete_managed_paths(kind):
        if relative_path in paths or (root / relative_path).exists():
            paths.add(relative_path)
    return sorted(paths)


def remove_obsolete_managed_files(kind: str, root: Path, templates: dict[str, str]) -> list[str]:
    manifest_payload, _ = read_manifest(kind, root)
    manifest_path_set = set(manifest_paths(manifest_payload)) if isinstance(manifest_payload, dict) else set()
    obsolete_paths = sorted((manifest_path_set | obsolete_managed_paths(kind)) - set(templates))
    removed: list[str] = []
    conflicts: list[str] = []
    marker = managed_marker(kind)
    for relative_path in obsolete_paths:
        target = root / relative_path
        if not target.exists():
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            conflicts.append(f"{relative_path} ({exc})")
            continue
        content_hash = sha256_text(content)
        manifest_hash = manifest_hash_for_path(manifest_payload, relative_path) if isinstance(manifest_payload, dict) else ""
        if marker in content or (manifest_hash and content_hash == manifest_hash):
            target.unlink()
            removed.append(relative_path)
            remove_empty_parents(root, target.parent)
            continue
        conflicts.append(relative_path)
    if conflicts:
        raise LooporaConflictError(
            f"refusing to remove or ignore non-Loopora obsolete {adapter_label(kind)} adapter files: "
            + ", ".join(conflicts)
        )
    return removed


def assert_targets_are_replaceable(kind: str, root: Path, templates: dict[str, str]) -> None:
    conflicts = []
    manifest_payload, _ = read_manifest(kind, root)
    marker = managed_marker(kind)
    for relative_path, content in templates.items():
        target = root / relative_path
        if not target.exists():
            continue
        try:
            existing = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            conflicts.append(f"{relative_path} ({exc})")
            continue
        manifest_hash = manifest_hash_for_path(manifest_payload, relative_path) if isinstance(manifest_payload, dict) else ""
        existing_hash = sha256_text(existing)
        if existing == content or marker in existing or (manifest_hash and existing_hash == manifest_hash):
            continue
        conflicts.append(relative_path)
    if conflicts:
        raise LooporaConflictError(
            f"refusing to overwrite non-Loopora {adapter_label(kind)} adapter files: " + ", ".join(conflicts)
        )


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def sha256_text(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def remove_empty_parents(root: Path, directory: Path) -> None:
    stop_dirs = {root, root / ".agents", root / ".codex", root / ".claude", root / ".opencode", root / ".loopora"}
    current = directory
    while current != current.parent and current not in stop_dirs:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
