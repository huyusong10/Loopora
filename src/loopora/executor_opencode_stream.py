from __future__ import annotations

from collections.abc import Callable

from loopora.executor_result_files import EXECUTOR_OUTPUT_MAX_BYTES
from loopora.executor_types import ExecutorError, RoleRequest

EmitEvent = Callable[[str, dict], None]


def initial_opencode_stream_state() -> dict:
    return {
        "latest_text": "",
        "text_parts": [],
        "text_size_bytes": 0,
    }


def handle_opencode_record(
    record: dict,
    state: dict,
    emit_event: EmitEvent,
    request: RoleRequest | None = None,
) -> None:
    if record.get("type") == "stdout":
        emit_event("codex_event", record)
        return
    event_type = record.get("type")
    if event_type == "step_start":
        emit_event("codex_event", {"type": "stdout", "message": "OpenCode step started"})
        return
    if event_type == "text":
        _handle_text_record(record, state, emit_event, request)
        return
    if event_type == "step_finish":
        _handle_step_finish_record(record, emit_event)


def _handle_text_record(
    record: dict,
    state: dict,
    emit_event: EmitEvent,
    request: RoleRequest | None,
) -> None:
    text = str((record.get("part") or {}).get("text") or "").strip()
    if not text:
        return
    text_size = len(text.encode("utf-8"))
    next_size = int(state.get("text_size_bytes") or 0) + text_size
    if next_size > EXECUTOR_OUTPUT_MAX_BYTES:
        role = request.role if request is not None else "unknown"
        raise ExecutorError(
            f"opencode output is too large for role={role}: "
            f"{next_size} bytes exceeds {EXECUTOR_OUTPUT_MAX_BYTES} bytes"
        )
    state["text_size_bytes"] = next_size
    state["latest_text"] = text
    state["text_parts"].append(text)
    emit_event("codex_event", {"type": "stdout", "message": text})


def _handle_step_finish_record(record: dict, emit_event: EmitEvent) -> None:
    tokens = ((record.get("part") or {}).get("tokens") or {})
    total = tokens.get("total")
    if total is not None:
        emit_event("codex_event", {"type": "stdout", "message": f"OpenCode step finished · tokens={total}"})
