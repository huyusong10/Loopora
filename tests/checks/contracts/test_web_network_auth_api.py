from __future__ import annotations

import re
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

import loopora.web as web_module
from loopora.web import build_app


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_app_auth_middleware_has_dedicated_boundary() -> None:
    web_source = (REPO_ROOT / "src" / "loopora" / "web.py").read_text(encoding="utf-8")
    auth_source = (REPO_ROOT / "src" / "loopora" / "web_auth_middleware.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_auth_middleware import install_auth_middleware" in web_source
    assert "def install_auth_middleware" in auth_source
    assert "def _auth_token_matches" in auth_source
    assert "def _auth_token_matches" not in web_source
    assert "web_auth_middleware.py" in design_source


def test_logo_assets_are_served(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/logo/logo.svg")
    assert response.status_code == HTTPStatus.OK
    assert "image/svg+xml" in response.headers["content-type"]


def test_network_mode_requires_auth_token_and_sets_cookie(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/")
    assert unauthorized.status_code == HTTPStatus.UNAUTHORIZED
    assert "Auth token required" in unauthorized.text

    unsupported_header = client.get("/", headers={"X-Other-Token": "secret-token"})
    assert unsupported_header.status_code == HTTPStatus.UNAUTHORIZED

    bearer_authorized = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")).get(
        "/api/loops",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert bearer_authorized.status_code == HTTPStatus.OK

    custom_header_authorized = TestClient(
        build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")
    ).get(
        "/api/loops",
        headers={"X-Loopora-Token": "secret-token"},
    )
    assert custom_header_authorized.status_code == HTTPStatus.OK

    authorized = client.get("/?token=secret-token")
    assert authorized.status_code == HTTPStatus.OK
    assert client.cookies.get("loopora_auth") == "secret-token"

    api_response = client.get("/api/loops")
    assert api_response.status_code == HTTPStatus.OK


def test_network_mode_auth_page_uses_request_locale_and_shared_styles(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/", headers={"Accept-Language": "zh-CN;q=0.1,en-US;q=0.9"})

    assert unauthorized.status_code == HTTPStatus.UNAUTHORIZED
    assert re.search(r'<html\s+lang="en"\s+data-locale="en"\s+data-theme="light"\s*>', unauthorized.text)
    assert "loopora:theme" in unauthorized.text
    assert "loopora:locale" in unauthorized.text
    assert "/static/app.css?v=" in unauthorized.text
    assert "<style>" not in unauthorized.text
    assert 'data-testid="auth-card"' in unauthorized.text
    assert 'data-testid="auth-copy-stack"' in unauthorized.text
    assert "Loopora · Auth token required" in unauthorized.text
    assert "Auth token required" in unauthorized.text
    assert "需要访问令牌" in unauthorized.text
    assert "X-Loopora-Token" in unauthorized.text
    assert "X-Other-Token" not in unauthorized.text
    assert 'class="auth-logo" src="/logo/logo-with-text-horizontal.svg" alt="" aria-hidden="true"' in unauthorized.text

    unauthenticated_css = client.get("/static/app.css")
    assert unauthenticated_css.status_code == HTTPStatus.OK
    assert "text/css" in unauthenticated_css.headers["content-type"]
    assert ".auth-shell {" in unauthenticated_css.text
    unauthenticated_logo = client.get("/logo/logo.svg")
    assert unauthenticated_logo.status_code == HTTPStatus.OK
    assert "image/svg+xml" in unauthenticated_logo.headers["content-type"]

    css = client.get("/static/app.css?token=secret-token")
    assert css.status_code == HTTPStatus.OK
    assert ".auth-shell {" in css.text
    assert ".auth-card {" in css.text
    assert ".auth-copy-stack {" in css.text
    assert '[data-theme="dark"] .auth-card {' in css.text
    assert 'html[data-theme="dark"] .auth-logo {' in css.text


def test_preferred_locale_from_accept_language_respects_q_values_and_supported_locales() -> None:
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=0.1,en-US;q=0.9") == "en"
    assert web_module._preferred_locale_from_accept_language("en-US;q=0.1,zh-CN;q=0.9") == "zh"
    assert web_module._preferred_locale_from_accept_language("fr-FR,zh-CN;q=0.8,en-US;q=0.6") == "zh"
    assert web_module._preferred_locale_from_accept_language("fr-FR,de-DE;q=0.8") == "en"
    assert web_module._preferred_locale_from_accept_language("en-US;q=0,zh-CN;q=0.6") == "zh"
    assert web_module._preferred_locale_from_accept_language("zh_CN;q=0.7,en-US;q=0.4") == "zh"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=bad,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=nan,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=inf,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=1.5,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=-0.1,en-US;q=0.4") == "en"


def test_network_mode_disables_native_dialog_endpoints(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/api/system/pick-directory?token=secret-token")
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED

    post_response = client.post(
        "/api/system/pick-directory?token=secret-token",
        json={"start_path": "/tmp"},
    )
    assert post_response.status_code == HTTPStatus.BAD_REQUEST
    assert "native dialogs are disabled in network mode" in post_response.json()["error"]

    reveal = client.post("/api/system/reveal-path?token=secret-token", json={"path": "/tmp"})
    assert reveal.status_code == HTTPStatus.BAD_REQUEST
    assert "native dialogs are disabled in network mode" in reveal.json()["error"]
