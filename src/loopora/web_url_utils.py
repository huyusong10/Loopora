from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

SAFE_FILENAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- ")
SENSITIVE_REDIRECT_QUERY_KEYS = {
    "access_token",
    "api_key",
    "auth_token",
    "id_token",
    "refresh_token",
    "token",
    "x_loopora_token",
    "x-loopora-token",
}
LOCAL_REDIRECT_QUERY_VALUE_KEYS = {"return_to"}


def is_sensitive_redirect_query_key(key: object) -> bool:
    return str(key or "").strip().lower() in SENSITIVE_REDIRECT_QUERY_KEYS


def is_local_redirect_query_value_key(key: object) -> bool:
    return str(key or "").strip().lower() in LOCAL_REDIRECT_QUERY_VALUE_KEYS


def redirect_query_requires_safe_local_cleanup(query: str) -> bool:
    return any(
        _redirect_query_item_requires_safe_local_cleanup(key, value)
        for key, value in parse_qsl(query, keep_blank_values=True)
    )


def safe_local_return_path(value: object) -> str | None:
    target = str(value or "").strip()
    if not target:
        return None
    if "\\" in target or any(ord(char) < 32 or ord(char) == 127 for char in target):
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    if not parts.path.startswith("/") or parts.path.startswith("//"):
        return None
    return urlunsplit(
        ("", "", parts.path or "/", _safe_redirect_query(parts.query), _safe_redirect_fragment(parts.fragment))
    )


def with_query_params(url: str, **params: object) -> str:
    parts = urlsplit(url)
    query = dict(_safe_redirect_query_items(parts.query))
    for key, value in params.items():
        if value is None:
            continue
        cleaned = _safe_redirect_query_item(key, str(value))
        if cleaned is None:
            continue
        query[cleaned[0]] = cleaned[1]
    return urlunsplit(
        ("", "", parts.path or "/", urlencode(query), _safe_redirect_fragment(parts.fragment))
    )


def _safe_redirect_query(query: str) -> str:
    return urlencode(_safe_redirect_query_items(query))


def _safe_redirect_query_items(query: str) -> list[tuple[str, str]]:
    return [
        cleaned
        for key, value in parse_qsl(query, keep_blank_values=True)
        if (cleaned := _safe_redirect_query_item(key, value)) is not None
    ]


def _safe_redirect_query_item(key: str, value: str) -> tuple[str, str] | None:
    if is_sensitive_redirect_query_key(key):
        return None
    if is_local_redirect_query_value_key(key):
        cleaned_value = safe_local_return_path(value)
        if not cleaned_value:
            return None
        return key, cleaned_value
    return key, value


def _redirect_query_item_requires_safe_local_cleanup(key: str, value: str) -> bool:
    if is_sensitive_redirect_query_key(key):
        return True
    if not is_local_redirect_query_value_key(key):
        return False
    target = str(value or "").strip()
    if not target:
        return False
    if safe_local_return_path(target) is None:
        return True
    parts = urlsplit(target)
    return redirect_query_requires_safe_local_cleanup(parts.query) or _redirect_fragment_requires_cleanup(parts.fragment)


def _safe_redirect_fragment(fragment: str) -> str:
    if not fragment or "=" not in fragment:
        return fragment
    parsed_items = parse_qsl(fragment, keep_blank_values=True)
    if not parsed_items:
        return fragment
    cleaned_items: list[tuple[str, str]] = []
    removed_sensitive = False
    for key, value in parsed_items:
        if is_sensitive_redirect_query_key(key):
            removed_sensitive = True
            continue
        cleaned_items.append((key, value))
    if not removed_sensitive:
        return fragment
    return urlencode(cleaned_items)


def _redirect_fragment_requires_cleanup(fragment: str) -> bool:
    if not fragment or "=" not in fragment:
        return False
    return any(is_sensitive_redirect_query_key(key) for key, _value in parse_qsl(fragment, keep_blank_values=True))


def safe_attachment_filename(filename: object, *, default: str = "download") -> str:
    return _safe_attachment_filename(filename, default=default, allow_unicode=False)


def _safe_attachment_filename(filename: object, *, default: str, allow_unicode: bool) -> str:
    raw = str(filename or "").strip() or default
    cleaned = "".join(_attachment_filename_char(char, allow_unicode=allow_unicode) for char in raw)
    cleaned = re.sub(r"\s*-\s*", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")
    return cleaned or default


def _attachment_filename_char(char: str, *, allow_unicode: bool) -> str:
    if char in SAFE_FILENAME_CHARS:
        return char
    if not allow_unicode:
        return "-"
    if char in {'"', "/", "\\"} or unicodedata.category(char).startswith("C"):
        return "-"
    return char


def attachment_content_disposition(filename: object, *, default: str = "download") -> str:
    fallback = safe_attachment_filename(filename, default=default)
    disposition = f'attachment; filename="{fallback}"'
    utf8_filename = _safe_attachment_filename(filename, default=default, allow_unicode=True)
    if utf8_filename != fallback:
        disposition = f"{disposition}; filename*=UTF-8''{quote(utf8_filename, safe='')}"
    return disposition
