from __future__ import annotations

from collections.abc import Mapping

from loopora.event_redaction_codex import redact_codex_event_payload

import re

SECRET_OMITTED = "<secret omitted>"

_SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "bearer_token",
    "cookie",
    "password",
    "private_key",
    "privatekey",
    "secret",
    "secret_token",
    "set_cookie",
    "token",
}

_SECRET_KEY_SUFFIXES = ("_api_key", "_authorization", "_cookie", "_password", "_private_key", "_secret", "_token")

_SECRET_COMPACT_KEY_SUFFIXES = (
    "apikey",
    "authorization",
    "authtoken",
    "bearertoken",
    "clientsecret",
    "cookie",
    "password",
    "privatekey",
    "secret",
    "secrettoken",
    "setcookie",
    "token",
)

_SECRET_ARG_PATTERN = re.compile(
    r"(?i)(--(?:access[-_]token|api[-_]key|auth(?:orization|[-_]token)|bearer[-_]token|client[-_]secret|cookie|id[-_]token|password|private[-_]key|proxy[-_]authorization|refresh[-_]token|secret(?:[-_]token)?|session[-_]token|set[-_]cookie|token|x[-_](?:api[-_]key|loopora[-_]token))(?:=|\s+))"
    r"(<secret omitted>|\"[^\"]*\"|'[^']*'|[^\s]+)"
)

_ENV_SECRET_PATTERN = re.compile(
    r"(?i)\b(([A-Z0-9_]*(?:API_KEY|AUTH_TOKEN|BEARER_TOKEN|CLIENT_SECRET|PRIVATE_KEY|TOKEN|SECRET|PASSWORD))=)(<secret omitted>|[^\s]+)"
)

_BEARER_SECRET_PATTERN = re.compile(r"(?i)\b((?:authorization:\s*)?bearer\s+)([A-Za-z0-9._~+/=-]+)")

_HEADER_SECRET_PATTERN = re.compile(
    r"(?i)\b((?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|x-loopora-token):\s*)([^\r\n]+)"
)

def key_is_secret(normalized_key: str) -> bool:
    compact_key = re.sub(r"[^a-z0-9]+", "", normalized_key)
    return (
        normalized_key in _SECRET_KEYS
        or normalized_key.endswith(_SECRET_KEY_SUFFIXES)
        or compact_key.endswith(_SECRET_COMPACT_KEY_SUFFIXES)
    )

def redact_secret_text(value: str) -> str:
    redacted = _SECRET_ARG_PATTERN.sub(lambda match: f"{match.group(1)}{SECRET_OMITTED}", value)
    redacted = _ENV_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{SECRET_OMITTED}", redacted)
    redacted = _BEARER_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{SECRET_OMITTED}", redacted)
    return _HEADER_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}{SECRET_OMITTED}", redacted)

_is_secret_key = key_is_secret
_redact_string = redact_secret_text

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
