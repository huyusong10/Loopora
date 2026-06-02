from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_api_spec_validate_reports_auto_generated_check_mode(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "exploratory-spec.md"
    spec_path.write_text(
        "# Task\n\nExplore a promising prototype direction.\n\n# Guardrails\n\n- Stay focused.\n",
        encoding="utf-8",
    )

    validate_response = client.get("/api/specs/validate", params={"path": str(spec_path)})
    assert validate_response.status_code == HTTPStatus.OK
    payload = validate_response.json()
    assert payload["ok"] is True
    assert payload["check_mode"] == "auto_generated"
    assert payload["check_count"] == 0


def test_api_spec_validate_rejects_legacy_headings(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "legacy-spec.md"
    spec_path.write_text("# Goal\n\nLegacy format.\n", encoding="utf-8")

    response = client.get("/api/specs/validate", params={"path": str(spec_path)})

    assert response.status_code == HTTPStatus.OK
    assert response.json()["ok"] is False
    assert "legacy spec headings" in response.json()["error"]


def test_api_spec_preview_returns_rendered_read_only_markdown(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "preview-spec.md"
    spec_path.write_text(
        "# Task\n\nShip a preview.\n\n# Done When\n\n- Render headings\n- Escape <script>alert('xss')</script>\n\n```js\nconsole.log('ok')\n```\n",
        encoding="utf-8",
    )

    preview_response = client.get("/api/specs/preview", params={"path": str(spec_path)})

    assert preview_response.status_code == HTTPStatus.OK
    payload = preview_response.json()
    assert payload["ok"] is True
    assert payload["path"] == str(spec_path.resolve())
    assert "# Task" in payload["content"]
    assert "<h1>Task</h1>" in payload["rendered_html"]
    assert "<script>" not in payload["rendered_html"]
    assert "&lt;script&gt;alert" in payload["rendered_html"]
    assert 'class="language-js"' in payload["rendered_html"]
    assert "console.log" in payload["rendered_html"]
