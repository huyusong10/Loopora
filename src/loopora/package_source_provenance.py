from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

SOURCE_PROVENANCE_FILENAME = "_build_provenance.json"
SOURCE_PROVENANCE_SCHEMA_VERSION = 1
SOURCE_TREE_STATUSES = {"clean", "dirty"}
UNKNOWN_SOURCE_PROVENANCE = {"revision": "unknown", "tree_status": "unknown"}
_REVISION_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


def package_source_provenance(*, source_root: Path, packaged_path: Path) -> dict[str, str]:
    live = git_source_provenance(source_root)
    if live["revision"] != "unknown":
        return live
    return read_source_provenance(packaged_path) or dict(UNKNOWN_SOURCE_PROVENANCE)


def git_source_provenance(source_root: Path) -> dict[str, str]:
    if _git_output(("rev-parse", "--is-inside-work-tree"), cwd=source_root) != "true":
        return dict(UNKNOWN_SOURCE_PROVENANCE)
    top_level = _git_output(("rev-parse", "--show-toplevel"), cwd=source_root)
    if not top_level or Path(top_level).resolve() != source_root.resolve():
        return dict(UNKNOWN_SOURCE_PROVENANCE)
    revision = _git_output(("rev-parse", "--short=12", "HEAD"), cwd=source_root).lower()
    if not _REVISION_PATTERN.fullmatch(revision):
        return dict(UNKNOWN_SOURCE_PROVENANCE)
    dirty = bool(_git_output(("status", "--porcelain", "--untracked-files=normal"), cwd=source_root))
    return {"revision": revision, "tree_status": "dirty" if dirty else "clean"}


def read_source_provenance(path: Path) -> dict[str, str] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalized_source_provenance(payload)


def normalized_source_provenance(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict) or value.get("schema_version") != SOURCE_PROVENANCE_SCHEMA_VERSION:
        return None
    revision = str(value.get("revision") or "").strip().lower()
    tree_status = str(value.get("tree_status") or "").strip()
    if not _REVISION_PATTERN.fullmatch(revision) or tree_status not in SOURCE_TREE_STATUSES:
        return None
    return {"revision": revision, "tree_status": tree_status}


def write_source_provenance(path: Path, provenance: dict[str, str]) -> None:
    normalized = normalized_source_provenance({"schema_version": SOURCE_PROVENANCE_SCHEMA_VERSION, **provenance})
    if normalized is None:
        raise ValueError("source provenance requires a Git revision and clean/dirty tree status")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"schema_version": SOURCE_PROVENANCE_SCHEMA_VERSION, **normalized}
    path.write_text(f"{json.dumps(payload, sort_keys=True)}\n", encoding="utf-8")


def _git_output(args: tuple[str, ...], *, cwd: Path) -> str:
    try:
        result = subprocess.run(("git", *args), cwd=cwd, text=True, capture_output=True, check=False, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
