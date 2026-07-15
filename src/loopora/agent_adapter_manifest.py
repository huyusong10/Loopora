from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopora.agent_adapter_templates import ADAPTER_MANAGED_SCHEMA_VERSION, ADAPTER_VERSION, MANAGED_MARKERS
from loopora.utils import utc_now



import yaml

def adapter_check(name: str, *, ok: bool, path: str = "", message: str = "") -> dict[str, str]:
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "path": path,
        "message": message,
    }

def adapter_label(kind: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(kind, kind)

def markdown_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        metadata = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return metadata if isinstance(metadata, dict) else {}

def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

CODEX_MANIFEST_RELATIVE_PATH = ".loopora/adapters/codex/manifest.json"
CLAUDE_MANIFEST_RELATIVE_PATH = ".loopora/adapters/claude/manifest.json"
OPENCODE_MANIFEST_RELATIVE_PATH = ".loopora/adapters/opencode/manifest.json"
MANIFEST_RELATIVE_PATHS = {
    "codex": CODEX_MANIFEST_RELATIVE_PATH,
    "claude": CLAUDE_MANIFEST_RELATIVE_PATH,
    "opencode": OPENCODE_MANIFEST_RELATIVE_PATH,
}
MANIFEST_RELATIVE_PATH = CODEX_MANIFEST_RELATIVE_PATH
OBSOLETE_MANAGED_PATHS = {
    "codex": (
        ".agents/skills/loopora-gen/SKILL.md",
        ".agents/skills/loopora-loop/SKILL.md",
    ),
    "claude": (
        ".claude/commands/loopora-gen.md",
        ".claude/commands/loopora-loop.md",
        ".claude/commands/loopora-plan.md",
        ".claude/commands/loopora-run.md",
        ".claude/skills/loopora-gen/SKILL.md",
        ".claude/skills/loopora-loop/SKILL.md",
    ),
    "opencode": (
        ".opencode/commands/loopora-gen.md",
        ".opencode/commands/loopora-loop.md",
    ),
}


def manifest_payload(kind: str, root: Path, managed_files: list[dict[str, str]]) -> dict[str, Any]:
    existing_manifest, _ = read_manifest(kind, root)
    installed_at = ""
    if isinstance(existing_manifest, dict):
        installed_at = str(existing_manifest.get("installed_at") or "").strip()
    return {
        "adapter": kind,
        "managed_schema_version": ADAPTER_MANAGED_SCHEMA_VERSION,
        "version": ADAPTER_VERSION,
        "installed_at": installed_at or utc_now(),
        "managed_files": managed_files,
    }


def read_manifest(kind: str, root: Path) -> tuple[dict[str, Any] | None, str]:
    path = root / manifest_relative_path(kind)
    if not path.exists():
        return None, ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(payload, dict) or payload.get("adapter") != kind:
        return None, f"manifest is not a {adapter_label(kind)} adapter manifest"
    return payload, ""


def manifest_paths(manifest_payload: dict[str, Any] | None) -> list[str]:
    files = manifest_payload.get("managed_files") if isinstance(manifest_payload, dict) else []
    if not isinstance(files, list):
        return []
    paths = [str(item.get("path") or "").strip() for item in files if isinstance(item, dict)]
    return sorted(path for path in paths if path)


def manifest_hash_for_path(manifest_payload: dict[str, Any] | None, relative_path: str) -> str:
    files = manifest_payload.get("managed_files") if isinstance(manifest_payload, dict) else []
    if not isinstance(files, list):
        return ""
    for item in files:
        if isinstance(item, dict) and item.get("path") == relative_path:
            return str(item.get("sha256") or "").strip()
    return ""


def obsolete_managed_paths(kind: str) -> set[str]:
    return set(OBSOLETE_MANAGED_PATHS.get(kind, ()))


def managed_marker(kind: str) -> str:
    return MANAGED_MARKERS[kind]


def manifest_relative_path(kind: str) -> str:
    return MANIFEST_RELATIVE_PATHS[kind]
