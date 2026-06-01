from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_HASH_BYTES = 10 * 1024 * 1024


def artifact_manifest(ref: Mapping[str, Any]) -> dict:
    absolute_path = str(ref.get("absolute_path") or "").strip()
    file_state = artifact_file_state(absolute_path)
    return {
        "kind": str(ref.get("kind") or "").strip(),
        "label": str(ref.get("label") or "").strip(),
        "relative_path": str(ref.get("relative_path") or "").strip(),
        "workspace_path": str(ref.get("workspace_path") or "").strip(),
        "absolute_path": absolute_path,
        **file_state,
    }


def artifact_file_state(absolute_path: str) -> dict:
    if not absolute_path:
        return {"exists": False, "size_bytes": None, "sha256": "", "hash_status": "missing_path"}
    try:
        path = Path(absolute_path)
        stat = path.stat()
    except OSError:
        return {"exists": False, "size_bytes": None, "sha256": "", "hash_status": "missing"}
    if not path.is_file():
        return {"exists": True, "size_bytes": stat.st_size, "sha256": "", "hash_status": "not_file"}
    if stat.st_size > MAX_HASH_BYTES:
        return {"exists": True, "size_bytes": stat.st_size, "sha256": "", "hash_status": "too_large"}
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return {"exists": True, "size_bytes": stat.st_size, "sha256": "", "hash_status": "unreadable"}
    return {"exists": True, "size_bytes": stat.st_size, "sha256": digest, "hash_status": "sha256"}


def evidence_ref_is_direct_proof(ref: Mapping[str, Any]) -> bool:
    label = str(ref.get("label") or "").lower()
    workspace_path = str(ref.get("workspace_path") or "").lower()
    return label.startswith(("proof-file:", "proof-artifact:")) or "/evidence/" in f"/{workspace_path}"


def dedupe_artifact_refs(value: object) -> list[dict]:
    refs: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for ref in list(value or []):
        if not isinstance(ref, Mapping):
            continue
        key = (
            str(ref.get("label") or "").strip(),
            str(ref.get("absolute_path") or "").strip(),
            str(ref.get("workspace_path") or "").strip(),
            str(ref.get("relative_path") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        refs.append(dict(ref))
    return refs
