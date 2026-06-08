from __future__ import annotations

from collections.abc import Mapping
import re
from pathlib import Path, PurePosixPath

from loopora.service_types import LooporaError


SYSTEM_PROMPT_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "system_prompts"
_UNRESOLVED_PLACEHOLDER_RE = re.compile(r"{{[A-Za-z][A-Za-z0-9_]*}}")


def system_prompt_asset_path(asset_ref: str) -> Path:
    normalized = str(asset_ref or "").strip().replace("\\", "/")
    parts = normalized.split("/")
    if not normalized or normalized.startswith("/") or any(not part or part in {".", ".."} for part in parts):
        raise LooporaError("system prompt asset reference must be a safe relative path")
    return SYSTEM_PROMPT_ASSET_DIR.joinpath(*PurePosixPath(normalized).parts)


def load_system_prompt_asset(asset_ref: str) -> str:
    path = system_prompt_asset_path(asset_ref)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LooporaError(f"missing system prompt asset: {asset_ref}") from exc
    except UnicodeDecodeError as exc:
        raise LooporaError(f"system prompt asset must be UTF-8 encoded: {asset_ref}") from exc


def render_system_prompt_asset(asset_ref: str, values: Mapping[str, object] | None = None) -> str:
    rendered = load_system_prompt_asset(asset_ref)
    for key, value in (values or {}).items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    unresolved = sorted(set(_UNRESOLVED_PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        raise LooporaError(f"unresolved placeholders in system prompt asset {asset_ref}: {', '.join(unresolved)}")
    return rendered
