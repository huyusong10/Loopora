from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from loopora.agent_adapter_managed_files import (
    remove_empty_parents,
    sha256_text,
)
from loopora.agent_adapter_manifest import (
    manifest_hash_for_path,
    manifest_paths,
    manifest_relative_path,
    managed_marker,
    obsolete_managed_paths,
    read_manifest,
)
from loopora.agent_adapter_templates import managed_templates
from loopora.branding import state_dir_for_workdir
from loopora.settings import db_path
from loopora.workdir_inputs import normalize_existing_workdir, workdir_path_state

AGENT_ADAPTERS = ("codex", "claude", "opencode")
DEV_RESET_SCOPES = ("all", "app")


def dev_reset_loopora_state(*, workdir: Path, apply: bool = False, scope: str = "all") -> dict[str, Any]:
    normalized_scope = _normalize_reset_scope(scope)
    workdir_state = _dev_reset_workdir_state(workdir, scope=normalized_scope)
    root = Path(str(workdir_state.get("workdir") or "."))
    planned: list[str] = []
    removed: list[str] = []
    skipped: list[str] = []
    db = db_path()
    app_database_present = db.exists()
    if app_database_present:
        planned.append(str(db))
        if apply:
            db.unlink()
            removed.append(str(db))
    for suffix in ("-wal", "-shm"):
        sidecar = db.with_name(db.name + suffix)
        if sidecar.exists():
            planned.append(str(sidecar))
            if apply:
                sidecar.unlink()
                removed.append(str(sidecar))
    if normalized_scope == "app":
        return {
            "workdir": str(root),
            "workdir_state": workdir_state,
            "scope": normalized_scope,
            "app_database_present": app_database_present,
            "dry_run": not apply,
            "planned": planned,
            "removed": removed,
            "skipped": skipped,
        }
    for adapter in AGENT_ADAPTERS:
        adapter_result = _remove_adapter_managed_files(root, adapter, apply=apply)
        planned.extend(adapter_result["planned"])
        removed.extend(adapter_result["removed"])
        skipped.extend(adapter_result["skipped"])
    state_dir = state_dir_for_workdir(root)
    if state_dir.exists():
        planned.append(str(state_dir))
        if apply:
            shutil.rmtree(state_dir)
            removed.append(str(state_dir))
    return {
        "workdir": str(root),
        "workdir_state": workdir_state,
        "scope": normalized_scope,
        "app_database_present": app_database_present,
        "dry_run": not apply,
        "planned": planned,
        "removed": removed,
        "skipped": skipped,
    }


def _dev_reset_workdir_state(workdir: Path, *, scope: str) -> dict[str, object]:
    if scope != "app":
        root = normalize_existing_workdir(workdir)
        return {"status": "ready", "workdir": str(root)}
    state = workdir_path_state(workdir)
    if str(state.get("workdir") or "").strip():
        return state
    return {**state, "workdir": str(Path().resolve(strict=False))}


def _normalize_reset_scope(scope: str) -> str:
    normalized = str(scope or "all").strip().lower()
    if normalized not in DEV_RESET_SCOPES:
        accepted = ", ".join(DEV_RESET_SCOPES)
        raise ValueError(f"dev reset scope must be one of: {accepted}")
    return normalized


def _remove_adapter_managed_files(root: Path, adapter: str, *, apply: bool) -> dict[str, list[str]]:
    manifest_payload, _error = read_manifest(adapter, root)
    paths = set(managed_templates(adapter))
    paths.update(manifest_paths(manifest_payload))
    paths.update(obsolete_managed_paths(adapter))
    paths.add(manifest_relative_path(adapter))
    removed: list[str] = []
    planned: list[str] = []
    skipped: list[str] = []
    marker = managed_marker(adapter)
    for relative_path in sorted(paths, key=lambda item: item.count("/"), reverse=True):
        target = root / relative_path
        if not target.exists() or target.is_dir():
            continue
        manifest_hash = manifest_hash_for_path(manifest_payload, relative_path) if isinstance(manifest_payload, dict) else ""
        if relative_path == manifest_relative_path(adapter) or _is_loopora_managed_file(target, marker, manifest_hash):
            planned.append(str(target))
            if apply:
                target.unlink()
                removed.append(str(target))
                remove_empty_parents(root, target.parent)
        else:
            skipped.append(str(target))
    return {"planned": planned, "removed": removed, "skipped": skipped}


def _is_loopora_managed_file(path: Path, marker: str, manifest_hash: str) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return marker in content or (bool(manifest_hash) and sha256_text(content) == manifest_hash)
