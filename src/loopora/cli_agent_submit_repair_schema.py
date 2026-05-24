from __future__ import annotations

import json
import re
from pathlib import Path


_SCHEMA_TYPE_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) expected (?P<expected>[A-Za-z_]+), got (?P<actual>[A-Za-z_]+)")
_SCHEMA_REQUIRED_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) is required")
_SCHEMA_EXTRA_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) is not allowed by output_schema")
_SCHEMA_ENUM_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) must be one of (?P<values>\[[^\]]+\])")


def result_file_null_placeholder_focus(result_file: Path) -> str:
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    result = payload.get("result") if isinstance(payload, dict) else None
    paths: list[str] = []
    _collect_null_paths(result, "$", paths)
    if not paths:
        return ""
    return "replace null placeholders before submit: " + _format_bounded_list(paths, limit=12)


def output_schema_error_hint(error: str, schema: dict) -> str:
    hints = output_schema_error_hints(error, schema)
    return hints[0] if hints else ""


def output_schema_error_hints(error: str, schema: dict, *, limit: int = 6) -> list[str]:
    hints: list[str] = []
    type_matches = list(_SCHEMA_TYPE_ERROR_RE.finditer(error))
    null_paths = [match.group("path") for match in type_matches if match.group("actual") == "null"]
    if len(null_paths) > 1:
        hints.append("replace null placeholders before submit: " + _format_bounded_list(null_paths, limit=6))
    for match in type_matches:
        hints.append(_schema_type_error_hint(match, schema))
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_REQUIRED_ERROR_RE.finditer(error):
        hints.append(f"add missing result field {match.group('path').removeprefix('$.')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_EXTRA_ERROR_RE.finditer(error):
        hints.append(f"remove non-schema result field {match.group('path').removeprefix('$.')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_ENUM_ERROR_RE.finditer(error):
        hints.append(f"{match.group('path')} must use one allowed value: {match.group('values')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    return list(dict.fromkeys(hints))[:limit]


def active_step_coverage_target_ids(active_step: dict) -> list[str]:
    judgment_contract = active_step.get("judgment_contract") if isinstance(active_step.get("judgment_contract"), dict) else {}
    ids: list[str] = []
    for item in list(judgment_contract.get("coverage_targets") or []):
        if isinstance(item, dict):
            target_id = str(item.get("id") or item.get("target_id") or "").strip()
            if target_id:
                ids.append(target_id)
    return list(dict.fromkeys(ids))


def _collect_null_paths(value: object, path: str, paths: list[str]) -> None:
    if value is None:
        paths.append(path)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _collect_null_paths(child, f"{path}.{key}", paths)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_null_paths(child, f"{path}[{index}]", paths)


def _schema_type_error_hint(match: re.Match[str], schema: dict) -> str:
    path = match.group("path")
    expected = match.group("expected")
    node = _schema_node_at_path(schema, path)
    shape = _schema_shape_hint(node)
    if shape:
        return f"{path} must be {shape}"
    return f"{path} must be {expected}; rewrite that value inside result"


def _format_bounded_list(items: list[str], *, limit: int) -> str:
    visible = items[:limit]
    suffix = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return ", ".join(visible) + suffix


def _schema_node_at_path(schema: dict, path: str) -> dict:
    node: object = schema
    for segment in _schema_path_segments(path):
        if not isinstance(node, dict):
            return {}
        if isinstance(segment, int):
            node = node.get("items")
        else:
            properties = node.get("properties") if isinstance(node.get("properties"), dict) else {}
            node = properties.get(segment)
    return node if isinstance(node, dict) else {}


def _schema_path_segments(path: str) -> list[str | int]:
    segments: list[str | int] = []
    for match in re.finditer(r"\.([A-Za-z0-9_-]+)|\[(\d+)\]", path):
        if match.group(1) is not None:
            segments.append(match.group(1))
        else:
            segments.append(int(match.group(2)))
    return segments


def _schema_shape_hint(node: dict) -> str:
    schema_type = str(node.get("type") or "").strip()
    if schema_type == "object":
        required = [str(item) for item in list(node.get("required") or []) if str(item).strip()]
        if required:
            return "an object with required fields: " + ", ".join(required)
        return "an object"
    if schema_type == "array":
        item_shape = _schema_shape_hint(node.get("items") if isinstance(node.get("items"), dict) else {})
        return f"an array of {item_shape}" if item_shape else "an array"
    if schema_type:
        return schema_type
    return ""
