from __future__ import annotations

import json
from pathlib import Path

from loopora.executor_output_parsing import parse_structured_output_from_text
from loopora.executor_types import ExecutorError, RoleRequest


EXECUTOR_OUTPUT_MAX_BYTES = 1_000_000


def write_executor_schema_file(request: RoleRequest) -> Path:
    schema_path = request.run_dir / f"{request.role}_schema.json"
    schema_path.write_text(json.dumps(request.output_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema_path


def write_executor_json_output(request: RoleRequest, payload: dict) -> None:
    request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_executor_json_object_output(
    request: RoleRequest,
    *,
    executor_label: str,
    invalid_json_message: str,
    non_object_message: str,
    allow_text_fallback: bool = False,
) -> dict:
    output_text = read_executor_output_text(request.output_path, role=request.role, executor_label=executor_label)
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        if allow_text_fallback:
            payload = parse_structured_output_from_text(output_text)
            if isinstance(payload, dict):
                return payload
        raise ExecutorError(invalid_json_message) from exc
    if not isinstance(payload, dict):
        raise ExecutorError(non_object_message)
    return payload


def read_executor_output_text(path: Path, *, role: str, executor_label: str) -> str:
    try:
        output_size = path.stat().st_size
    except OSError as exc:
        raise ExecutorError(f"{executor_label} output file is not readable for role={role}") from exc
    if output_size > EXECUTOR_OUTPUT_MAX_BYTES:
        raise ExecutorError(
            f"{executor_label} output file is too large for role={role}: "
            f"{output_size} bytes exceeds {EXECUTOR_OUTPUT_MAX_BYTES} bytes"
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ExecutorError(f"role={role} produced non-UTF-8 output") from exc
