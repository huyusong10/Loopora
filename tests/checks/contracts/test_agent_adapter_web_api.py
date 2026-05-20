from __future__ import annotations

from agent_adapter_helpers import *

def test_agent_adapter_web_api_reports_status_and_mutates_implemented_hosts(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    workdir = tmp_path / "project"
    workdir.mkdir()

    status_response = client.get("/api/agent-adapters", params={"workdir": str(workdir)})
    assert status_response.status_code == 200
    payload = status_response.json()
    statuses = {item["adapter"]: item["status"] for item in payload["adapters"]}
    assert statuses == {
        "codex": "not_installed",
        "claude": "not_installed",
        "opencode": "not_installed",
    }

    install_response = client.post("/api/agent-adapters/codex/install", json={"workdir": str(workdir)})
    assert install_response.status_code == 200
    assert install_response.json()["status"] == "installed"
    assert (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").exists()

    uninstall_response = client.post("/api/agent-adapters/codex/uninstall", json={"workdir": str(workdir)})
    assert uninstall_response.status_code == 200
    assert uninstall_response.json()["status"] == "not_installed"
    assert not (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").exists()

    claude_install_response = client.post("/api/agent-adapters/claude/install", json={"workdir": str(workdir)})
    assert claude_install_response.status_code == 200
    assert claude_install_response.json()["status"] == "installed"
    assert (workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md").exists()

    opencode_install_response = client.post("/api/agent-adapters/opencode/install", json={"workdir": str(workdir)})
    assert opencode_install_response.status_code == 200
    assert opencode_install_response.json()["status"] == "installed"
    assert (workdir / ".opencode" / "commands" / "loopora-plan.md").exists()

def test_agent_adapter_web_api_reports_invalid_json(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    invalid_json = client.post(
        "/api/agent-adapters/codex/install",
        content="{",
        headers={"content-type": "application/json"},
    )
    non_object = client.post("/api/agent-adapters/codex/uninstall", json=["not", "an", "object"])

    assert invalid_json.status_code == 400
    assert "invalid JSON body" in invalid_json.json()["error"]
    assert non_object.status_code == 400
    assert non_object.json()["error"] == "request body must be a JSON object"

def test_agent_web_health_check_requires_loopora_runtime_payload(monkeypatch) -> None:
    class FakeResponse:
        status = 200

        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    monkeypatch.setattr(agent_web, "urlopen", lambda *_args, **_kwargs: FakeResponse(b'{"hello": true}'))
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742") is False

    monkeypatch.setattr(
        agent_web,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742") is True

    monkeypatch.setattr(
        agent_web,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"app_home": "/tmp/other-loopora", "running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742", expected_app_home="/tmp/current-loopora") is False

    monkeypatch.setattr(
        agent_web,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"app_home": "/tmp/current-loopora", "running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742", expected_app_home="/tmp/current-loopora") is True
