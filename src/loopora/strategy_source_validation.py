from __future__ import annotations

"""Shared Strategy Source validation helpers used by compatibility facades."""

import re
from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_constants import STRATEGY_SOURCE_VERSION
from loopora.strategy_source_errors import WorkflowError

STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
WORKFLOW_SAFE_IDENTIFIER_RE = STRATEGY_SOURCE_SAFE_IDENTIFIER_RE


def normalize_strategy_source_identifier(value: object, *, field_name: str) -> str:
    if value is None:
        normalized = ""
    elif not isinstance(value, str):
        raise WorkflowError(f"{field_name} must be a string")
    else:
        normalized = value.strip()
    if not normalized:
        raise WorkflowError(f"{field_name} is required")
    if not STRATEGY_SOURCE_SAFE_IDENTIFIER_RE.fullmatch(normalized):
        raise WorkflowError(f"{field_name} must use letters, numbers, dot, underscore, or dash")
    return normalized


def normalize_workflow_identifier(value: object, *, field_name: str) -> str:
    return normalize_strategy_source_identifier(value, field_name=field_name)


def normalize_optional_strategy_source_identifier(
    value: object,
    *,
    default: str,
    field_name: str,
) -> str:
    if value is None:
        return normalize_strategy_source_identifier(default, field_name=field_name)
    if isinstance(value, str) and not value.strip():
        return normalize_strategy_source_identifier(default, field_name=field_name)
    return normalize_strategy_source_identifier(value, field_name=field_name)


def normalize_optional_workflow_identifier(
    value: object,
    *,
    default: str,
    field_name: str,
) -> str:
    return normalize_optional_strategy_source_identifier(value, default=default, field_name=field_name)


def normalize_strategy_source_version(value: Any, *, field_name: str = "strategy source version") -> int:
    if value is None:
        return STRATEGY_SOURCE_VERSION
    if isinstance(value, str) and not value.strip():
        return STRATEGY_SOURCE_VERSION
    if isinstance(value, bool):
        raise WorkflowError(f"{field_name} must be an integer")
    if isinstance(value, float):
        raise WorkflowError(f"{field_name} must be an integer")
    try:
        version = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise WorkflowError(f"{field_name} must be an integer") from exc
    if version != STRATEGY_SOURCE_VERSION:
        raise WorkflowError(f"unsupported {field_name}: {version}")
    return version


def normalize_workflow_version(value: Any, *, field_name: str = "workflow version") -> int:
    return normalize_strategy_source_version(value, field_name=field_name)


def normalize_string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if not isinstance(value, list):
        raise WorkflowError(f"{field_name} must be a string or array of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise WorkflowError(f"{field_name} must contain only strings")
        normalized = item.strip()
        if normalized:
            result.append(normalized)
    return result


def unknown_keys(value: Mapping[str, Any], allowed_keys: set[str]) -> list[str]:
    return sorted(str(key) for key in value if str(key) not in allowed_keys)
