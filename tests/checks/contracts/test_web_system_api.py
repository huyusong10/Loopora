from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

import loopora.web as web_module
from loopora.web import build_app


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_api_guard_has_dedicated_route_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    system_source = (REPO_ROOT / "src" / "loopora" / "web_system_api.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_system_api import register_system_api_routes" in editor_source
    assert "register_system_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _guard_system_api_request",
        "def _system_request_is_same_origin",
        '"/api/system/pick-directory"',
        '"/api/system/reveal-path"',
    ):
        assert marker in system_source
        assert marker not in editor_source
    assert "web_system_api.py" in design_source


def test_api_reveal_path_uses_native_host_shortcut(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_reveal(path: str) -> str:
        called.append(path)
        return path

    monkeypatch.setattr(web_module, "reveal_path", fake_reveal)
    response = client.post("/api/system/reveal-path", json={"path": str(sample_workdir)})

    assert response.status_code == HTTPStatus.OK
    assert response.json()["ok"] is True
    assert called == [str(sample_workdir)]


def test_system_picker_requires_post_and_same_origin(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_pick_directory(start_path: str | None = None) -> str:
        called.append(start_path or "")
        return str(sample_workdir)

    monkeypatch.setattr(web_module, "pick_directory", fake_pick_directory)

    old_get = client.get(f"/api/system/pick-directory?start_path={sample_workdir}")
    assert old_get.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert called == []

    cross_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://evil.example"},
    )
    assert cross_origin.status_code == HTTPStatus.FORBIDDEN
    assert "same origin" in cross_origin.json()["error"]
    assert called == []

    malformed_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://testserver:bad"},
    )
    assert malformed_origin.status_code == HTTPStatus.FORBIDDEN
    assert "same origin" in malformed_origin.json()["error"]
    assert called == []

    same_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://testserver"},
    )
    assert same_origin.status_code == HTTPStatus.OK
    assert same_origin.json()["path"] == str(sample_workdir)
    assert called == [str(sample_workdir)]


def test_system_reveal_rejects_cross_origin_before_callback(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_reveal(path: str) -> str:
        called.append(path)
        return path

    monkeypatch.setattr(web_module, "reveal_path", fake_reveal)
    response = client.post(
        "/api/system/reveal-path",
        json={"path": str(sample_workdir)},
        headers={"Referer": "http://evil.example/page"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert "same origin" in response.json()["error"]
    assert called == []
