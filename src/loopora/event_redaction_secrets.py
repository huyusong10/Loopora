from __future__ import annotations

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
