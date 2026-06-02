from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_task_alignment_skill_api_is_not_registered() -> None:
    client = TestClient(build_app())

    assert client.get("/api/skills/loopora-task-alignment").status_code == HTTPStatus.NOT_FOUND
    assert (
        client.post("/api/skills/loopora-task-alignment/install", json={"target": "codex"}).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert client.get("/api/skills/loopora-task-alignment/download").status_code == HTTPStatus.NOT_FOUND
