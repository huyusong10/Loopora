from __future__ import annotations

from pathlib import Path

from loopora.local_workdir_artifacts import state_dir_for_ready_workdir, stored_local_asset_path
from loopora.settings import app_home


def orphan_bundle_dirs(registry_rows: list[dict], bundle_ids: set[str]) -> list[dict]:
    orphan_bundle_dirs = []
    orphan_bundle_paths: set[str] = set()
    bundle_root = app_home() / "bundles"
    if bundle_root.exists():
        for path in sorted(item for item in bundle_root.iterdir() if item.is_dir()):
            if path.name not in bundle_ids:
                orphan_bundle_dirs.append({"bundle_id": path.name, "path": str(path)})
                orphan_bundle_paths.add(str(path))
    for row in registry_rows:
        if row.get("resource_type") != "bundle" or row.get("state") == "cleaned":
            continue
        bundle_id = str(row.get("resource_id") or "").strip()
        path = stored_local_asset_path(row.get("path"))
        if path is None:
            continue
        if path.exists() and (bundle_id not in bundle_ids or row.get("state") == "orphaned"):
            normalized_path = str(path)
            if normalized_path not in orphan_bundle_paths:
                orphan_bundle_dirs.append({"bundle_id": bundle_id, "path": normalized_path})
                orphan_bundle_paths.add(normalized_path)
    return orphan_bundle_dirs


def orphan_run_dirs(registry_rows: list[dict], run_ids: set[str], known_workdirs: set[str]) -> list[dict]:
    orphan_run_dirs = []
    orphan_run_paths: set[str] = set()
    for row in registry_rows:
        if row.get("resource_type") != "run" or row.get("state") == "cleaned":
            continue
        run_id = str(row.get("resource_id") or "").strip()
        path = stored_local_asset_path(row.get("path"))
        if path is None:
            continue
        if path.exists() and (run_id not in run_ids or row.get("state") == "orphaned"):
            normalized_path = str(path)
            if normalized_path not in orphan_run_paths:
                orphan_run_dirs.append(
                    {
                        "run_id": run_id,
                        "workdir": str(row.get("workdir") or ""),
                        "path": normalized_path,
                        "source": "registry",
                    }
                )
                orphan_run_paths.add(normalized_path)
    for workdir, root in _ready_workdir_asset_roots(known_workdirs, "runs"):
        for path in sorted(item for item in root.iterdir() if item.is_dir()):
            if path.name in run_ids:
                continue
            normalized_path = str(path)
            if normalized_path in orphan_run_paths:
                continue
            orphan_run_dirs.append(
                {
                    "run_id": path.name,
                    "workdir": workdir,
                    "path": normalized_path,
                    "source": "recent_workdir",
                }
            )
            orphan_run_paths.add(normalized_path)
    return orphan_run_dirs


def orphan_alignment_dirs(registry_rows: list[dict], alignment_session_ids: set[str], known_workdirs: set[str]) -> list[dict]:
    orphan_alignment_dirs = []
    orphan_alignment_paths: set[str] = set()
    for workdir, root in _ready_workdir_asset_roots(known_workdirs, "alignment_sessions"):
        for path in sorted(item for item in root.iterdir() if item.is_dir()):
            if path.name not in alignment_session_ids:
                orphan_alignment_dirs.append({"session_id": path.name, "workdir": workdir, "path": str(path)})
                orphan_alignment_paths.add(str(path))
    for row in registry_rows:
        if row.get("resource_type") != "alignment_session" or row.get("state") == "cleaned":
            continue
        session_id = str(row.get("resource_id") or "").strip()
        path = stored_local_asset_path(row.get("path"))
        if path is None:
            continue
        if path.exists() and (session_id not in alignment_session_ids or row.get("state") == "orphaned"):
            normalized_path = str(path)
            if normalized_path not in orphan_alignment_paths:
                orphan_alignment_dirs.append(
                    {"session_id": session_id, "workdir": str(row.get("workdir") or ""), "path": normalized_path}
                )
                orphan_alignment_paths.add(normalized_path)
    return orphan_alignment_dirs


def _ready_workdir_asset_roots(known_workdirs: set[str], child: str) -> list[tuple[str, Path]]:
    roots = []
    for workdir in sorted(path for path in known_workdirs if path):
        state_dir = state_dir_for_ready_workdir(workdir)
        if state_dir is None:
            continue
        root = state_dir / child
        if root.exists():
            roots.append((workdir, root))
    return roots
