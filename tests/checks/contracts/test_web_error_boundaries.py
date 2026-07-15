from __future__ import annotations

from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from loopora import agent_web, cli_agent_runtime_support, cli_root_commands, web
from loopora.cli import app as cli_app
from loopora.service_types import LooporaError
from loopora.web import build_app


def test_unhandled_errors_are_redacted_for_api_and_page_clients() -> None:
    secret = "database unavailable at /private/project/loopora.sqlite"

    class FailingService:
        def latest_run_event_id(self, _run_id: str) -> int:
            raise RuntimeError(secret)

        def list_loops(self) -> list:
            raise RuntimeError(secret)

    client = TestClient(build_app(service=FailingService()), raise_server_exceptions=False)

    api_response = client.get("/api/runs/run_test/events")
    page_response = client.get("/bundles")

    assert api_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert api_response.json() == {"error": "internal server error"}
    assert page_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert page_response.headers["content-type"].startswith("text/html")
    assert 'data-testid="web-error-page"' in page_response.text.replace("'", '"')
    assert "/support" not in page_response.text
    assert secret not in api_response.text + page_response.text


def test_domain_errors_keep_json_for_api_and_safe_html_for_pages() -> None:
    secret = "permission denied: /private/project"

    class FailingService:
        def latest_run_event_id(self, _run_id: str) -> int:
            raise LooporaError(secret)

        def list_loops(self) -> list:
            raise LooporaError(secret)

    client = TestClient(build_app(service=FailingService()), raise_server_exceptions=False)

    api_response = client.get("/api/runs/run_test/events")
    page_response = client.get("/bundles")

    assert api_response.status_code == HTTPStatus.BAD_REQUEST
    assert api_response.json() == {"error": secret}
    assert page_response.status_code == HTTPStatus.BAD_REQUEST
    assert page_response.headers["content-type"].startswith("text/html")
    assert secret not in page_response.text


def test_http_and_validation_errors_follow_client_content_type(service_factory) -> None:
    client = TestClient(build_app(service=service_factory(scenario="success")), raise_server_exceptions=False)

    page_response = client.get("/missing-loopora-page")
    api_response = client.get("/api/unknown-loopora-resource")
    validation_response = client.get("/bundles/derive/export", headers={"accept": "application/json"})

    assert page_response.status_code == HTTPStatus.NOT_FOUND
    assert page_response.headers["content-type"].startswith("text/html")
    assert api_response.json() == {"error": "Not Found"}
    assert validation_response.status_code == HTTPStatus.BAD_REQUEST
    assert validation_response.json() == {"error": "request validation failed"}


def test_web_app_refuses_unprotected_remote_access_before_service_initialization(monkeypatch) -> None:
    service_initialized = False

    def fail_if_initialized():
        nonlocal service_initialized
        service_initialized = True
        raise AssertionError("service must not initialize before remote access is validated")

    monkeypatch.setattr(web, "create_service", fail_if_initialized)

    with pytest.raises(LooporaError, match="refusing to bind a non-loopback host"):
        build_app(bind_host="0.0.0.0")

    assert service_initialized is False


def test_remote_web_requires_auth_unless_unsafe_access_is_explicit() -> None:
    protected = build_app(service=object(), bind_host="0.0.0.0", auth_token="network-secret")
    rejected = TestClient(protected, raise_server_exceptions=False).get("/")

    assert rejected.status_code == HTTPStatus.UNAUTHORIZED
    assert protected.state.access_state["auth_enabled"] is True

    unsafe = build_app(service=object(), bind_host="0.0.0.0", allow_unsafe_open=True)
    assert unsafe.state.access_state["remote_access_enabled"] is True
    assert unsafe.state.access_state["auth_enabled"] is False


def test_serve_does_not_echo_the_configured_auth_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_app(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(cli_root_commands, "build_app", fake_build_app)
    monkeypatch.setattr(cli_root_commands.uvicorn, "run", lambda *_args, **_kwargs: None)

    result = CliRunner().invoke(
        cli_app,
        ["serve", "--host", "0.0.0.0", "--auth-token", "do-not-print-this-token"],
    )

    assert result.exit_code == 0, result.output
    assert "do-not-print-this-token" not in result.output
    assert "token form" in result.output
    assert captured["auth_token"] == "do-not-print-this-token"
    assert captured["allow_unsafe_open"] is False


def test_agent_web_discovery_never_starts_a_detached_service(monkeypatch) -> None:
    monkeypatch.setattr(agent_web, "_loopora_web_responds", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(agent_web, "_port_is_available", lambda *_args, **_kwargs: True)

    state = agent_web.ensure_local_web_service(preferred_port=9123)

    assert state["status"] == "not_running"
    assert state["started"] is False
    assert state["start_required"] is True
    assert state["port"] == 9123
    assert not hasattr(agent_web, "_start_web_process")


def test_agent_web_fallback_returns_a_relative_path_and_foreground_command(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {
            "status": "not_running",
            "base_url": "http://127.0.0.1:9123",
            "reused": False,
            "started": False,
            "start_required": True,
            "start_available": True,
            "port": 9123,
            "warning": "not running",
        },
    )
    result = {"run_path": "/runs/run_test"}

    cli_agent_runtime_support.attach_web_url(result, path_key="run_path", url_key="run_url", no_web=False)

    assert result["run_url"] == "/runs/run_test"
    assert result["run_url_status"] == "relative_path_web_not_running"
    assert result["run_url_web_start_command"].endswith("loopora serve --host 127.0.0.1 --port 9123")
    assert "--open" not in result["run_url_web_start_command"]
