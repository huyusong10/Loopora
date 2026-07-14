from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import sqlite3

from strategy_source_architecture_test_support import design_boundary_source

from fastapi.testclient import TestClient
from typer.testing import CliRunner

import loopora.web as web_module
import loopora.executor_runtime_readiness as executor_readiness_module
from loopora.executor_real import RealCodexExecutor
from loopora.system_dialogs import SystemDialogError
from loopora.web import build_app
from loopora import cli, web_bind_preflight
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION
from loopora.start_guidance import start_guidance_lines, start_guidance_payload

from cli_first_use_docs_test_support import COMPLETE_FIT_REVIEW, complete_fit_guidance_payload


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_api_guard_has_dedicated_route_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    system_source = (REPO_ROOT / "src" / "loopora" / "web_system_api.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.web_system_api import register_system_api_routes" in editor_source
    assert "register_system_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _guard_system_api_request",
        "def _system_request_is_same_origin",
        '"/api/system/pick-directory"',
        '"/api/system/reveal-path"',
        '"/api/system/executor-readiness"',
        "def _guard_same_origin_request",
    ):
        assert marker in system_source
        assert marker not in editor_source
    assert "web_system_api.py" in design_source


def test_executor_readiness_treats_embedded_runtime_as_host_managed(service_factory) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).post(
        "/api/system/executor-readiness",
        json={"executor_kind": "codex", "executor_mode": "preset"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "schema_version": 1,
        "executor_kind": "codex",
        "executor_mode": "preset",
        "executor_label": "Codex",
        "command_name": "codex",
        "status": "ready",
        "blocking": False,
        "readiness_kind": "managed_runtime",
        "next_action_kind": "start_or_continue_conversation",
        "available_executor_kinds": [],
    }


def test_executor_readiness_blocks_missing_real_cli_and_lists_available_alternative(
    monkeypatch,
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    service.executor_factory = RealCodexExecutor
    monkeypatch.setattr(
        executor_readiness_module.shutil,
        "which",
        lambda command: "/usr/local/bin/claude" if command == "claude" else None,
    )

    response = TestClient(build_app(service=service)).post(
        "/api/system/executor-readiness",
        json={"executor_kind": "codex", "executor_mode": "preset"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["readiness_kind"] == "executable_not_found"
    assert response.json()["blocking"] is True
    assert response.json()["available_executor_kinds"] == ["claude"]
    assert "/usr/local/bin" not in response.text


def test_executor_readiness_requires_custom_command_before_runtime_start(service_factory) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).post(
        "/api/system/executor-readiness",
        json={"executor_kind": "custom", "executor_mode": "command", "command_cli": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["readiness_kind"] == "command_required"
    assert response.json()["next_action_kind"] == "configure_executor_command"
    assert response.json()["blocking"] is True


def test_executor_readiness_rejects_cross_origin_probe(service_factory) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).post(
        "/api/system/executor-readiness",
        json={"executor_kind": "codex", "executor_mode": "preset"},
        headers={"Origin": "http://evil.example"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert "same origin" in response.json()["error"]


def test_web_port_suggestion_survives_stacked_local_port_conflicts(monkeypatch) -> None:
    probed_ports: list[int] = []

    def fake_probe(_host: str, port: int) -> None:
        probed_ports.append(port)
        if port < 8793:
            raise OSError("occupied")

    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", fake_probe)

    assert web_bind_preflight.next_available_web_port(host="127.0.0.1", port=8742) == 8793
    assert probed_ports[0] == 8743
    assert probed_ports[-1] == 8793
    assert 8742 not in probed_ports


def test_first_use_web_route_blocks_until_app_state_is_recovered(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("PRAGMA user_version = 1")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", lambda *_args: None)

    start_payload = start_guidance_payload(COMPLETE_FIT_REVIEW, workdir=workdir, preflight_web_route=True)
    start_action = _route_action(start_payload, "open_web_creation_choices")
    fit_payload = complete_fit_guidance_payload(workdir=workdir, preflight_web_route=True)
    fit_action = _route_action(fit_payload, "open_web_creation_choices")

    assert start_action["preflight_status"] == "available"
    assert start_action["command_ready"] is False
    assert start_action["command_blockers"] == ["app_state_not_ready"]
    assert start_action["readiness_blockers"] == [
        {
            "kind": "app_state_not_ready",
            "status": "development_reset_required",
            "recovery_action": "preview_app_database_reset",
        }
    ]
    assert start_payload["start_guidance_summary"]["web_route_command_ready"] is False
    assert start_payload["start_guidance_summary"]["web_route_command_blockers"] == ["app_state_not_ready"]
    assert start_payload["route_action_command_blockers"]["return_to_agent"] == ["same_agent_entry_required", "app_state_not_ready"]
    assert start_payload["route_action_command_blockers"]["run_after_review"] == ["app_state_not_ready", "ready_review_required"]
    start_text = "\n".join(start_guidance_lines(start_payload))
    assert (
        "Local App/Web state needs attention" in start_text,
        "Web command after blockers are resolved:" in start_text,
        "Requested Web command, currently unavailable:" not in start_text,
    ) == (True, True, True)
    assert fit_action["command_ready"] is False
    assert fit_action["command_blockers"] == ["app_state_not_ready"]
    assert fit_payload["fit_guidance_summary"]["web_route_command_blockers"] == ["app_state_not_ready"]
    assert fit_payload["route_action_command_blockers"]["return_to_agent"] == ["same_agent_entry_required", "app_state_not_ready"]
    assert fit_payload["route_action_command_blockers"]["run_after_review"] == ["app_state_not_ready", "ready_review_required"]


def test_first_use_web_route_explains_future_app_state_recovery(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", lambda *_args: None)

    payload = start_guidance_payload(COMPLETE_FIT_REVIEW, workdir=workdir, preflight_web_route=True)
    action = _route_action(payload, "open_web_creation_choices")
    text = "\n".join(start_guidance_lines(payload))

    assert action["readiness_blockers"] == [
        {"kind": "app_state_not_ready", "status": "future_version", "recovery_action": "use_matching_loopora_version_or_reset"}
    ]
    assert ("matching or newer Loopora version" in text, "reset or temporary-home recovery" not in text) == (True, True)


def test_fit_plain_web_route_explains_future_app_state_recovery(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", lambda *_args: None)

    result = CliRunner().invoke(
        cli.app,
        [
            "fit",
            "--workdir",
            str(workdir),
            "--task",
            "Ship reviewed work",
            "--fit-reason",
            "multi-round evidence",
            "--fake-done",
            "looks done without proof",
            "--evidence",
            "contract tests",
            "--tradeoffs",
                "protect data",
                "--details",
            ],
    )

    assert result.exit_code == 0, result.stdout
    assert (
        "Fit Guide/Web choices:" in result.stdout,
        "matching or newer Loopora version" in result.stdout,
        "reset or temporary-home recovery" not in result.stdout,
    ) == (True, True, True)


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


def _route_action(payload: dict[str, object], kind: str) -> dict[str, object]:
    for action in payload["route_actions_after_strong_fit"]:
        if action["kind"] == kind:
            return action
    raise AssertionError(f"missing route action: {kind}")


def test_api_reveal_path_missing_target_uses_stable_error(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_path = sample_workdir / "missing-secret"

    response = client.post("/api/system/reveal-path", json={"path": str(missing_path)})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "path does not exist"
    assert response.json()["error_code"] == "path_not_found"
    assert str(missing_path) not in response.text


def test_api_reveal_path_redacts_native_error_details(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    def fake_reveal(path: str) -> str:
        raise SystemDialogError("path could not be opened", code="path_reveal_failed", detail=f"permission denied: {path}")

    monkeypatch.setattr(web_module, "reveal_path", fake_reveal)

    response = client.post("/api/system/reveal-path", json={"path": str(sample_workdir)})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"error": "path could not be opened", "error_code": "path_reveal_failed"}
    assert "permission denied" not in response.text
    assert str(sample_workdir) not in response.text


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
