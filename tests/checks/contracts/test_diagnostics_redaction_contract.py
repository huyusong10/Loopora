from __future__ import annotations

import json
import logging

from loopora.diagnostics import LooporaJsonFormatter, get_logger, log_exception
from loopora.event_redaction import redact_sensitive_text
from loopora.settings import app_home, configure_logging


EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT = 15


def _read_service_log_records() -> list[dict]:
    log_path = app_home() / "logs" / "service.log"
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_structured_logging_redacts_sensitive_values_before_write() -> None:
    configure_logging()
    logger = get_logger("loopora.tests.diagnostics")

    try:
        raise RuntimeError("failed with Authorization: Bearer ERROR_SECRET_MARKER")
    except RuntimeError as exc:
        log_exception(
            logger,
            "test.logging.secret",
            "Starting command --token TOKEN_SECRET_MARKER",
            error=exc,
            auth_token="CONTEXT_TOKEN_SECRET_MARKER",
            private_key="PRIVATE_KEY_SECRET_MARKER",
            headers={
                "Authorization": "Bearer HEADER_SECRET_MARKER",
                "Cookie": "COOKIE_SECRET_MARKER",
                "private-key": "NESTED_PRIVATE_KEY_SECRET_MARKER",
            },
            oauth={
                "accessToken": "ACCESS_TOKEN_SECRET_MARKER",
                "bearerToken": "BEARER_TOKEN_SECRET_MARKER",
                "clientSecret": "CLIENT_SECRET_MARKER",
            },
        )

    log_text = (app_home() / "logs" / "service.log").read_text(encoding="utf-8")
    _assert_markers_omitted(
        log_text,
        "TOKEN_SECRET_MARKER", "CONTEXT_TOKEN_SECRET_MARKER", "HEADER_SECRET_MARKER", "COOKIE_SECRET_MARKER",
        "PRIVATE_KEY_SECRET_MARKER", "NESTED_PRIVATE_KEY_SECRET_MARKER", "ACCESS_TOKEN_SECRET_MARKER",
        "BEARER_TOKEN_SECRET_MARKER", "CLIENT_SECRET_MARKER", "ERROR_SECRET_MARKER",
    )

    payload = next(item for item in _read_service_log_records() if item["event"] == "test.logging.secret")
    assert payload["message"] == "Starting command --token <secret omitted>"
    assert payload["context"]["auth_token"] == "<secret omitted>"
    assert payload["context"]["private_key"] == "<secret omitted>"
    assert payload["context"]["headers"]["Authorization"] == "<secret omitted>"
    assert payload["context"]["headers"]["Cookie"] == "<secret omitted>"
    assert payload["context"]["headers"]["private-key"] == "<secret omitted>"
    assert payload["context"]["oauth"]["accessToken"] == "<secret omitted>"
    assert payload["context"]["oauth"]["bearerToken"] == "<secret omitted>"
    assert payload["context"]["oauth"]["clientSecret"] == "<secret omitted>"
    assert payload["error"]["message"] == "failed with Authorization: <secret omitted>"


def test_json_formatter_redacts_manually_attached_context_before_write() -> None:
    logger = get_logger("loopora.tests.manual_formatter")
    record = logger.makeRecord(
        logger.name,
        logging.WARNING,
        __file__,
        123,
        "Manual command --token MESSAGE_SECRET_MARKER",
        (),
        None,
        extra={
            "event": "test.logging.manual_secret",
            "workdir": "Cookie: sid=WORKDIR_SECRET_MARKER",
            "context": {
                "auth_token": "CONTEXT_TOKEN_SECRET_MARKER",
                "headers": {
                    "Authorization": "Bearer HEADER_SECRET_MARKER",
                    "Cookie": "sid=COOKIE_SECRET_MARKER",
                },
                "refreshToken": "REFRESH_TOKEN_SECRET_MARKER",
                "nested": ["x-api-key: NESTED_SECRET_MARKER"],
            },
        },
    )

    payload = json.loads(LooporaJsonFormatter().format(record))
    log_text = json.dumps(payload, ensure_ascii=False)

    _assert_markers_omitted(
        log_text,
        "MESSAGE_SECRET_MARKER", "WORKDIR_SECRET_MARKER", "CONTEXT_TOKEN_SECRET_MARKER", "HEADER_SECRET_MARKER",
        "COOKIE_SECRET_MARKER", "REFRESH_TOKEN_SECRET_MARKER", "NESTED_SECRET_MARKER",
    )
    assert payload["message"] == "Manual command --token <secret omitted>"
    assert payload["workdir"] == "Cookie: <secret omitted>"
    assert payload["context"]["auth_token"] == "<secret omitted>"
    assert payload["context"]["refreshToken"] == "<secret omitted>"
    assert payload["context"]["headers"]["Authorization"] == "<secret omitted>"
    assert payload["context"]["headers"]["Cookie"] == "<secret omitted>"
    assert payload["context"]["nested"] == ["x-api-key: <secret omitted>"]


def test_sensitive_text_redacts_common_secret_aliases() -> None:
    redacted = redact_sensitive_text(
        "\n".join(
            [
                "tool --private-key PRIVATE_KEY_SECRET_MARKER --client-secret=CLIENT_SECRET_MARKER --x-api-key X_API_KEY_SECRET_MARKER",
                "tool --x-loopora-token LOOPORA_TOKEN_SECRET_MARKER",
                "tool --access-token ACCESS_TOKEN_FLAG_SECRET_MARKER --refresh-token REFRESH_TOKEN_FLAG_SECRET_MARKER --id-token ID_TOKEN_FLAG_SECRET_MARKER --session-token SESSION_TOKEN_FLAG_SECRET_MARKER",
                "tool --proxy-authorization PROXY_AUTH_FLAG_SECRET_MARKER --set-cookie=SET_COOKIE_FLAG_SECRET_MARKER --cookie COOKIE_FLAG_SECRET_MARKER",
                "tool --authorization AUTHORIZATION_FLAG_SECRET_MARKER",
                "PRIVATE_KEY=ENV_PRIVATE_KEY_SECRET_MARKER CLIENT_SECRET=ENV_CLIENT_SECRET_MARKER",
                "Proxy-Authorization: Basic PROXY_AUTH_SECRET_MARKER",
            ]
        )
    )

    _assert_markers_omitted(
        redacted,
        "PRIVATE_KEY_SECRET_MARKER", "CLIENT_SECRET_MARKER", "X_API_KEY_SECRET_MARKER", "LOOPORA_TOKEN_SECRET_MARKER",
        "ACCESS_TOKEN_FLAG_SECRET_MARKER", "REFRESH_TOKEN_FLAG_SECRET_MARKER", "ID_TOKEN_FLAG_SECRET_MARKER",
        "SESSION_TOKEN_FLAG_SECRET_MARKER", "PROXY_AUTH_FLAG_SECRET_MARKER", "SET_COOKIE_FLAG_SECRET_MARKER",
        "COOKIE_FLAG_SECRET_MARKER", "AUTHORIZATION_FLAG_SECRET_MARKER", "ENV_PRIVATE_KEY_SECRET_MARKER",
        "ENV_CLIENT_SECRET_MARKER", "PROXY_AUTH_SECRET_MARKER",
    )
    assert redacted.count("<secret omitted>") == EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT


def _assert_markers_omitted(text: str, *markers: str) -> None:
    for marker in markers:
        assert marker not in text
