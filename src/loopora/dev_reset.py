from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from loopora.agent_adapter_managed_files import (
    manifest_hash_for_path,
    manifest_paths,
    manifest_relative_path,
    managed_marker,
    obsolete_managed_paths,
    read_manifest,
    remove_empty_parents,
    sha256_text,
)
from loopora.agent_adapter_templates import managed_templates
from loopora.branding import state_dir_for_workdir
from loopora.settings import db_path

AGENT_ADAPTERS = ("codex", "claude", "opencode")


def dev_reset_loopora_state(*, workdir: Path, apply: bool = False) -> dict[str, Any]:
    root = workdir.expanduser().resolve()
    planned: list[str] = []
    removed: list[str] = []
    skipped: list[str] = []
    db = db_path()
    if db.exists():
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
    return {"workdir": str(root), "dry_run": not apply, "planned": planned, "removed": removed, "skipped": skipped}


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
