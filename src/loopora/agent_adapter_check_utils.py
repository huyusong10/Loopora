from __future__ import annotations

from pathlib import Path
from typing import Any

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
