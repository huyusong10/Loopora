from __future__ import annotations

"""Codex event payload redaction."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

PAYLOAD_OMITTED = "<payload omitted>"
MAX_CODEX_MESSAGE_LENGTH = 4000
MAX_CODEX_ITEM_TEXT_LENGTH = 4000
_CODEX_PASSTHROUGH_KEYS = {
    "type",
    "step_id",
    "step_order",
    "role",
    "role_name",
    "archetype",
    "iter",
    "invocation_id",
    "alignment_status",
    "prompt_omitted",
    "json_schema_omitted",
    "token_omitted",
    "command_truncated",
    "message_truncated",
    "summary_truncated",
    "payload_omitted",
    "omitted_keys",
    "arg_count",
}
_CODEX_PREVIEW_KEYS = ("message", "summary")
_CODEX_STRUCTURED_KEYS = {"error", "item"}

RedactContainer = Callable[[object], object]
RedactPreviewString = Callable[..., tuple[str, bool]]


@dataclass(frozen=True)
class CodexRedactionCallbacks:
    redact_container: RedactContainer
    redact_preview_string: RedactPreviewString


def redact_codex_event_payload(
    payload: Mapping[str, object],
    *,
    redact_container: RedactContainer,
    redact_preview_string: RedactPreviewString,
) -> dict:
    callbacks = CodexRedactionCallbacks(
        redact_container=redact_container,
        redact_preview_string=redact_preview_string,
    )
    sanitized: dict[str, object] = {}
    for key in _CODEX_PASSTHROUGH_KEYS:
        if key in payload:
            sanitized[key] = callbacks.redact_container(payload[key])

    for key in _CODEX_PREVIEW_KEYS:
        if key in payload:
            sanitized[key], was_truncated = callbacks.redact_preview_string(
                payload[key],
                max_length=MAX_CODEX_MESSAGE_LENGTH,
            )
            if was_truncated:
                sanitized[f"{key}_truncated"] = True

    if "error" in payload:
        sanitized["error"] = _redact_error(payload["error"], callbacks)
    if "item" in payload:
        sanitized["item"] = _redact_codex_item(payload["item"], callbacks)

    omitted_keys = _codex_omitted_payload_keys(payload)
    if omitted_keys:
        sanitized["payload_omitted"] = True
        sanitized["omitted_keys"] = omitted_keys
    return sanitized


def _codex_omitted_payload_keys(payload: Mapping[str, object]) -> list[str]:
    allowed_keys = _CODEX_PASSTHROUGH_KEYS | set(_CODEX_PREVIEW_KEYS) | _CODEX_STRUCTURED_KEYS
    return sorted(str(key) for key in payload if str(key) not in allowed_keys)


def _redact_error(value: object, callbacks: CodexRedactionCallbacks) -> object:
    if not isinstance(value, Mapping):
        message, was_truncated = callbacks.redact_preview_string(value, max_length=MAX_CODEX_MESSAGE_LENGTH)
        return {"message": message, "message_truncated": was_truncated} if was_truncated else {"message": message}
    sanitized: dict[str, object] = {}
    for key in ("message", "type", "code"):
        if key in value:
            sanitized[str(key)] = callbacks.redact_container(value[key])
    if not sanitized:
        sanitized["message"] = PAYLOAD_OMITTED
    return sanitized


def _redact_codex_item(value: object, callbacks: CodexRedactionCallbacks) -> dict:
    if not isinstance(value, Mapping):
        return {}
    item_type = str(value.get("type", "") or "").strip()
    sanitized: dict[str, object] = {"type": callbacks.redact_preview_string(item_type, max_length=MAX_CODEX_ITEM_TEXT_LENGTH)[0]} if item_type else {}
    if item_type == "command_execution":
        _redact_command_execution_item(value, sanitized, callbacks)
    elif item_type == "file_change":
        _redact_file_change_item(value, sanitized, callbacks)
    elif item_type == "todo_list":
        _redact_todo_list_item(value, sanitized, callbacks)
    elif item_type == "agent_message":
        _redact_agent_message_item(value, sanitized, callbacks)
    elif item_type:
        sanitized["payload_omitted"] = True
    return sanitized


def _redact_command_execution_item(
    value: Mapping[str, object],
    sanitized: dict[str, object],
    callbacks: CodexRedactionCallbacks,
) -> None:
    if "command" in value:
        sanitized["command"], command_truncated = callbacks.redact_preview_string(
            value["command"],
            max_length=MAX_CODEX_MESSAGE_LENGTH,
        )
        if command_truncated:
            sanitized["command_truncated"] = True
    if "aggregated_output" in value:
        sanitized["aggregated_output"], output_truncated = callbacks.redact_preview_string(
            value["aggregated_output"],
            max_length=MAX_CODEX_ITEM_TEXT_LENGTH,
        )
        if output_truncated:
            sanitized["aggregated_output_truncated"] = True
    for key in ("exit_code", "status"):
        if key in value:
            sanitized[key] = callbacks.redact_container(value[key])


def _redact_file_change_item(
    value: Mapping[str, object],
    sanitized: dict[str, object],
    callbacks: CodexRedactionCallbacks,
) -> None:
    changes = value.get("changes")
    if isinstance(changes, list):
        sanitized["changes"] = [_redact_file_change(change, callbacks) for change in changes if isinstance(change, Mapping)]


def _redact_todo_list_item(
    value: Mapping[str, object],
    sanitized: dict[str, object],
    callbacks: CodexRedactionCallbacks,
) -> None:
    items = value.get("items")
    if isinstance(items, list):
        sanitized["items"] = [_redact_todo_item(item, callbacks) for item in items if isinstance(item, Mapping)]


def _redact_agent_message_item(
    value: Mapping[str, object],
    sanitized: dict[str, object],
    callbacks: CodexRedactionCallbacks,
) -> None:
    if "text" not in value:
        return
    sanitized["text"], text_truncated = callbacks.redact_preview_string(
        value["text"],
        max_length=MAX_CODEX_ITEM_TEXT_LENGTH,
    )
    if text_truncated:
        sanitized["text_truncated"] = True


def _redact_file_change(value: Mapping[str, object], callbacks: CodexRedactionCallbacks) -> dict:
    sanitized: dict[str, object] = {}
    for key in ("path", "status", "operation", "kind"):
        if key in value:
            sanitized[key] = callbacks.redact_container(value[key])
    return sanitized


def _redact_todo_item(value: Mapping[str, object], callbacks: CodexRedactionCallbacks) -> dict:
    sanitized: dict[str, object] = {}
    for key in ("text", "content", "title"):
        if key in value:
            sanitized[key], was_truncated = callbacks.redact_preview_string(
                value[key],
                max_length=MAX_CODEX_ITEM_TEXT_LENGTH,
            )
            if was_truncated:
                sanitized[f"{key}_truncated"] = True
    for key in ("completed", "status"):
        if key in value:
            sanitized[key] = callbacks.redact_container(value[key])
    return sanitized
