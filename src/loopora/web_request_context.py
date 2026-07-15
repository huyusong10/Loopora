from __future__ import annotations

import ipaddress
import math

from fastapi import Request

from loopora.branding import APP_AUTH_COOKIE, APP_AUTH_HEADER


def _request_wants_json(request: Request) -> bool:
    if request.url.path.startswith("/api/"):
        return True
    for raw_item in str(request.headers.get("accept") or "").split(","):
        media_type = raw_item.split(";", 1)[0].strip().lower()
        if media_type == "application/json" or media_type.endswith("+json"):
            return True
    return False


def _preferred_request_locale(request: Request) -> str:
    return _preferred_locale_from_accept_language(request.headers.get("accept-language"))


def _preferred_locale_from_accept_language(accept_language: str | None) -> str:
    header = str(accept_language or "").strip()
    if not header:
        return "en"

    candidates = _accept_language_locale_candidates(header)
    if not candidates:
        return "en"

    candidates.sort()
    return candidates[0][2]


def _accept_language_locale_candidates(header: str) -> list[tuple[float, int, str]]:
    candidates: list[tuple[float, int, str]] = []
    for position, raw_item in enumerate(header.split(",")):
        candidate = _accept_language_locale_candidate(raw_item, position=position)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _accept_language_locale_candidate(raw_item: str, *, position: int) -> tuple[float, int, str] | None:
    item = raw_item.strip()
    if not item:
        return None
    language_tag, *params = [segment.strip() for segment in item.split(";")]
    locale = _locale_for_language_tag(language_tag)
    if not locale:
        return None

    q_value = _accept_language_q_value(params)
    if q_value <= 0:
        return None
    return -q_value, position, locale


def _locale_for_language_tag(language_tag: str) -> str:
    normalized_tag = str(language_tag or "").strip().lower().replace("_", "-")
    if normalized_tag.startswith("zh"):
        return "zh"
    if normalized_tag.startswith("en"):
        return "en"
    return ""


def _accept_language_q_value(params: list[str]) -> float:
    for param in params:
        key, sep, value = param.partition("=")
        if sep and key.strip().lower() == "q":
            return _float_or_zero(value)
    return 1.0


def _float_or_zero(value: str) -> float:
    try:
        parsed = float(value.strip())
    except ValueError:
        return 0.0
    return parsed if math.isfinite(parsed) and 0.0 <= parsed <= 1.0 else 0.0


def _build_access_state(*, bind_host: str, bind_port: int, auth_token: str | None) -> dict[str, object]:
    normalized_auth = (auth_token or "").strip() or None
    remote_access_enabled = not _is_loopback_host(bind_host)
    return {
        "bind_host": bind_host,
        "bind_port": bind_port,
        "auth_token": normalized_auth,
        "auth_enabled": bool(normalized_auth),
        "remote_access_enabled": remote_access_enabled,
        "native_dialogs_enabled": not remote_access_enabled,
    }


def _extract_request_token(request: Request) -> str | None:
    bearer = request.headers.get("authorization", "")
    if bearer.lower().startswith("bearer "):
        token = bearer.split(" ", 1)[1].strip()
        if token:
            return token

    header_token = request.headers.get(APP_AUTH_HEADER, "").strip()
    if header_token:
        return header_token

    query_token = request.query_params.get("token", "").strip()
    if query_token:
        return query_token

    cookie_token = request.cookies.get(APP_AUTH_COOKIE, "").strip()
    if cookie_token:
        return cookie_token
    return None


def _is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False
