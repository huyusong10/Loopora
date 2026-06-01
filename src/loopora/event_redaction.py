from __future__ import annotations

from collections.abc import Mapping

from loopora.event_redaction_codex import redact_codex_event_payload
from loopora.event_redaction_secrets import SECRET_OMITTED
from loopora.event_redaction_secrets import key_is_secret as _is_secret_key
from loopora.event_redaction_secrets import redact_secret_text as _redact_string

PROMPT_OMITTED = "<prompt omitted>"
JSON_SCHEMA_OMITTED = "<json schema omitted>"
MAX_ALIGNMENT_EVENT_TEXT_LENGTH = 2000
MAX_ALIGNMENT_COMMAND_MESSAGE_LENGTH = 500

_PROMPT_KEYS = {
    "compiled_prompt",
    "prompt",
    "prompt_markdown",
    "prompt_text",
    "system_prompt",
}
_JSON_SCHEMA_KEYS = {
    "input_schema",
    "json_schema",
    "output_schema",
    "schema",
    "schema_json",
}
_ALIGNMENT_OMITTED_KEYS = _PROMPT_KEYS | _JSON_SCHEMA_KEYS | {"bundle_yaml"}


def redact_run_event_payload(event_type: str, payload: Mapping[str, object] | None) -> dict:
    if not isinstance(payload, Mapping):
        return {}
    if str(event_type or "").strip() == "codex_event":
        return redact_codex_event_payload(
            payload,
            redact_container=_redact_container,
            redact_preview_string=_redact_preview_string,
        )
    return {
        str(key): _redact_value(str(key), value)
        for key, value in payload.items()
    }


def redact_alignment_event_payload(event_type: str, payload: Mapping[str, object] | None) -> dict:
    if not isinstance(payload, Mapping):
        return {}
    sanitized = (
        redact_codex_event_payload(
            payload,
            redact_container=_redact_container,
            redact_preview_string=_redact_preview_string,
        )
        if str(event_type or "").strip() == "codex_event"
        else _redact_alignment_mapping(payload)
    )
    return _truncate_alignment_event_payload(sanitized)


def redact_sensitive_value(key: str, value: object) -> object:
    return _redact_value(str(key), value)


def redact_sensitive_text(value: object) -> str:
    return _redact_string(str(value or ""))


def _redact_alignment_mapping(payload: Mapping[str, object]) -> dict:
    sanitized: dict[str, object] = {}
    for key, value in payload.items():
        normalized_key = _normalized_key(str(key))
        if normalized_key in _ALIGNMENT_OMITTED_KEYS:
            sanitized[f"{key}_omitted"] = True
            continue
        sanitized[str(key)] = _redact_value(str(key), value)
    return sanitized


def _truncate_alignment_event_payload(payload: dict) -> dict:
    sanitized = dict(payload)
    if "message" in sanitized:
        message_limit = (
            MAX_ALIGNMENT_COMMAND_MESSAGE_LENGTH
            if sanitized.get("type") == "command"
            else MAX_ALIGNMENT_EVENT_TEXT_LENGTH
        )
        sanitized["message"] = _truncate_alignment_event_text(sanitized["message"], limit=message_limit)
        if sanitized.get("type") == "command":
            sanitized["command_truncated"] = True
    if "error" in sanitized:
        sanitized["error"] = _truncate_alignment_event_text(sanitized["error"], limit=MAX_ALIGNMENT_EVENT_TEXT_LENGTH)
    return sanitized


def _truncate_alignment_event_text(value: object, *, limit: int) -> str:
    text = _redact_string(str(value or ""))
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def _normalized_key(key: str) -> str:
    return str(key or "").strip().lower().replace("-", "_")


def _redact_value(key: str, value: object) -> object:
    normalized_key = _normalized_key(key)
    if normalized_key in _PROMPT_KEYS:
        return PROMPT_OMITTED
    if normalized_key in _JSON_SCHEMA_KEYS:
        return JSON_SCHEMA_OMITTED
    if _is_secret_key(normalized_key):
        return SECRET_OMITTED
    return _redact_container(value)


def _redact_container(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _redact_value(str(key), child) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact_container(child) for child in value]
    if isinstance(value, tuple):
        return [_redact_container(child) for child in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_preview_string(value: object, *, max_length: int) -> tuple[str, bool]:
    redacted = _redact_string(str(value or ""))
    if len(redacted) <= max_length:
        return redacted, False
    suffix = "\n... <truncated>"
    return redacted[: max(0, max_length - len(suffix))].rstrip() + suffix, True
