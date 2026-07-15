from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def structured_bool_is_true(value: object) -> bool:
    """Return true only for literal booleans from structured contracts."""
    return value is True


def runtime_task_language_from_text(value: object) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in str(value or "")) else "en"


def runtime_task_language(compiled_spec: Mapping[str, object]) -> str:
    fragments = [
        compiled_spec.get("goal"),
        compiled_spec.get("constraints"),
        compiled_spec.get("success_surface"),
        compiled_spec.get("fake_done_states"),
        compiled_spec.get("evidence_preferences"),
        compiled_spec.get("residual_risk"),
        compiled_spec.get("checks"),
        compiled_spec.get("role_notes"),
    ]
    return runtime_task_language_from_text(fragments)


def runtime_task_text(language: str, english: str, chinese: str) -> str:
    return chinese if str(language or "").strip().lower() == "zh" else english


def structured_non_negative_int(value: object, *, default: int = 0) -> int:
    """Return a non-negative JSON integer, rejecting bools and coerced strings."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    return default


def structured_optional_non_negative_int(value: object) -> int | None:
    """Return a non-negative JSON integer or None when the value must fail closed."""
    normalized = structured_non_negative_int(value, default=-1)
    return normalized if normalized >= 0 else None


def coerced_int(value: object, *, default: int = 0) -> int:
    """Return an integer from legacy/event payload values, rejecting bools."""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerced_non_negative_int(
    value: object,
    *,
    default: int = 0,
    strict: bool = False,
    field_name: str = "value",
) -> int:
    """Return a non-negative legacy integer, optionally failing closed on invalid values."""
    if isinstance(value, bool):
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return default
    if value in (None, ""):
        return default
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer") from exc
        return default
    if integer < 0:
        if strict:
            raise ValueError(f"{field_name} must be a non-negative integer")
        return default
    return integer


def coerced_optional_non_negative_int(value: object) -> int | None:
    """Return a non-negative legacy integer or None when the value must fail closed."""
    normalized = coerced_non_negative_int(value, default=-1)
    return normalized if normalized >= 0 else None


def structured_finite_number(value: object, *, default: float = 0.0) -> float:
    """Return a finite JSON number, rejecting bools and coerced strings."""
    normalized = structured_optional_finite_number(value)
    return default if normalized is None else normalized


def structured_optional_finite_number(value: object) -> float | None:
    """Return a finite JSON number or None when the value must fail closed."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def make_id(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{stamp}_{uuid4().hex[:8]}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def append_jsonl(path: Path, payload: dict) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
