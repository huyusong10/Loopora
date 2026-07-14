from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


_SIGNED_TOKEN_SECRET = secrets.token_bytes(32)


def token_matches(provided_token: str | None, expected_token: object) -> bool:
    expected = str(expected_token or "")
    provided = str(provided_token or "")
    return bool(expected and provided) and hmac.compare_digest(provided, expected)


def sign_scoped_token(scope: str, value: str) -> str:
    scoped_value = str(value or "")
    signature = _scoped_token_signature(scope, scoped_value)
    return f"v1.{scoped_value}.{signature}"


def scoped_token_matches(provided_token: str | None, *, scope: str, value: str) -> bool:
    token = str(provided_token or "")
    scoped_value = str(value or "")
    prefix = f"v1.{scoped_value}."
    if not token.startswith(prefix):
        return False
    expected = f"{prefix}{_scoped_token_signature(scope, scoped_value)}"
    return token_matches(token, expected)


def _scoped_token_signature(scope: str, value: str) -> str:
    message = f"{scope}\0{value}".encode()
    digest = hmac.new(_SIGNED_TOKEN_SECRET, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
