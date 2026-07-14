from __future__ import annotations

from http import HTTPStatus
import json
import shlex

from agent_adapter_test_support import (
    Path,
    TestClient,
    agent_web,
    build_app,
)
from loopora import agent_adapter_command_prefix
from loopora import local_web_service
from loopora import web_service_probe
from loopora.branding import APP_AUTH_ENV
from loopora.branding import APP_HOME_ENV
from loopora.settings import load_recent_workdirs


def test_agent_adapter_web_api_projects_current_host_without_session_identity(service_factory, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "private-thread-id")
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
    client = TestClient(build_app(service=service_factory(scenario="success")))
    workdir = tmp_path / "project"
    workdir.mkdir()

    payload = client.get("/api/agent-adapters", params={"workdir": str(workdir)}).json()
    targetless = client.get("/api/agent-adapters").json()

    assert payload["current_agent_host"] == targetless["current_agent_host"] == {
        "state": "detected",
        "adapter": "codex",
        "detected_adapters": ["codex"],
        "selection_required": False,
        "command_ready": True,
        "command_blockers": [],
    }
    assert "private-thread-id" not in json.dumps(payload)


def test_agent_adapter_web_api_reports_status_and_mutates_implemented_hosts(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    workdir = tmp_path / "project"
    workdir.mkdir()

    status_response = client.get("/api/agent-adapters", params={"workdir": str(workdir)})
    assert status_response.status_code == HTTPStatus.OK
    payload = status_response.json()
    statuses = {item["adapter"]: item["status"] for item in payload["adapters"]}
    assert statuses == {
        "codex": "not_installed",
        "claude": "not_installed",
        "opencode": "not_installed",
    }
    assert load_recent_workdirs() == []

    install_response = client.post("/api/agent-adapters/codex/install", json={"workdir": str(workdir)})
    assert install_response.status_code == HTTPStatus.OK
    install_payload = install_response.json()
    assert install_payload["status"] == "installed"
    assert "/loopora-plan\n\nLoopora fit:" in install_payload["first_task_message_example"]
    assert install_payload["first_task_message_example_state"] == {
        "kind": "generic_orientation_example",
        "source": "generic_example",
        "copy_allowed": False,
        "completed_review": False,
    }
    assert install_payload["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert install_payload["first_task_handoff_policy"]["fallback_source"] == "generic_example"
    raw_fit_command = f"loopora fit --workdir {shlex.quote(str(workdir.resolve()))}"
    assert install_payload["first_task_handoff_policy"]["fit_command"] == agent_adapter_command_prefix.copyable_loopora_command(raw_fit_command)
    assert "paste its copyable /loopora-plan handoff as one Agent message" in install_payload["first_task_handoff_policy"]["copy_rule"]
    assert f"--workdir {shlex.quote(str(workdir.resolve()))}" in install_payload["first_task_handoff_policy"]["copy_rule"]
    assert install_payload["first_task_handoff_policy"]["fit_command"] in install_payload["first_task_handoff_policy"]["copy_rule"]
    assert "generic orientation example only as a review starting point" in install_payload["first_task_handoff_policy"]["copy_rule"]
    doctor_command = install_payload["next_commands"]["doctor"]
    web_start_command = install_payload["next_commands"]["web_start"]
    assert "loopora doctor --workdir" in doctor_command
    assert str(workdir) in doctor_command
    assert web_start_command.endswith(f"loopora serve --open --workdir {workdir} --host 127.0.0.1 --port 8742")
    assert (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").exists()
    assert load_recent_workdirs() == [str(workdir.resolve())]
    _assert_same_agent_setup_routes(client, workdir)

    uninstall_response = client.post("/api/agent-adapters/codex/uninstall", json={"workdir": str(workdir)})
    assert uninstall_response.status_code == HTTPStatus.OK
    uninstall_payload = uninstall_response.json()
    assert uninstall_payload["status"] == "not_installed"
    assert ".agents/skills/loopora-plan/SKILL.md" in uninstall_payload["removed_files"]
    assert uninstall_payload["kept_files"] == []
    assert not (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").exists()

    claude_install_response = client.post("/api/agent-adapters/claude/install", json={"workdir": str(workdir)})
    assert claude_install_response.status_code == HTTPStatus.OK
    assert claude_install_response.json()["status"] == "installed"
    assert (workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md").exists()

    opencode_install_response = client.post("/api/agent-adapters/opencode/install", json={"workdir": str(workdir)})
    assert opencode_install_response.status_code == HTTPStatus.OK
    assert opencode_install_response.json()["status"] == "installed"
    assert (workdir / ".opencode" / "commands" / "loopora-plan.md").exists()


def _assert_same_agent_setup_routes(client: TestClient, workdir: Path) -> None:
    page = client.get("/same-agent")
    legacy_page = client.get("/tools")

    assert page.status_code == legacy_page.status_code == HTTPStatus.OK
    assert f'data-project-scope-option="{workdir.resolve()}"' in page.text
    assert 'id="agent-adapter-recent-workdir-options"' in page.text
    assert 'data-agent-adapter-recent-workdir="' not in page.text
    assert str(workdir.resolve()) in page.text
    assert str(workdir.resolve()) in legacy_page.text


def test_agent_adapter_web_api_previews_uninstall_without_deleting(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    workdir = tmp_path / "project"
    workdir.mkdir()

    install_response = client.post("/api/agent-adapters/codex/install", json={"workdir": str(workdir)})
    preview_response = client.post("/api/agent-adapters/codex/uninstall-preview", json={"workdir": str(workdir)})
    preview_payload = preview_response.json()

    assert install_response.status_code == HTTPStatus.OK
    assert preview_response.status_code == HTTPStatus.OK
    assert preview_payload["status"] == "dry_run"
    assert preview_payload["dry_run"] is True
    assert ".agents/skills/loopora-plan/SKILL.md" in preview_payload["removed_files"]
    assert preview_payload["kept_files"] == []
    assert (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").exists()


def test_agent_adapter_web_api_preserves_configured_app_home_in_copyable_commands(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    app_home = tmp_path / "custom app home"
    workdir = tmp_path / "project with spaces"
    app_home.mkdir()
    workdir.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    install_response = client.post("/api/agent-adapters/codex/install", json={"workdir": str(workdir)})
    payload = install_response.json()
    status_response = client.get("/api/agent-adapters", params={"workdir": str(workdir)})
    codex_status = next(item for item in status_response.json()["adapters"] if item["adapter"] == "codex")
    command_prefix = f"{APP_HOME_ENV}={shlex.quote(str(app_home))} "

    assert install_response.status_code == HTTPStatus.OK
    assert status_response.status_code == HTTPStatus.OK
    assert payload["next_commands"]["doctor"].startswith(command_prefix)
    assert payload["next_commands"]["check"].startswith(command_prefix)
    assert payload["next_commands"]["agent_check"].startswith(command_prefix)
    assert payload["next_commands"]["web_start"].startswith(command_prefix)
    assert payload["next_commands"]["support"].startswith(command_prefix)
    assert f"loopora doctor --workdir {shlex.quote(str(workdir.resolve()))}" in payload["next_commands"]["doctor"]
    assert f"loopora serve --open --workdir {shlex.quote(str(workdir.resolve()))}" in payload["next_commands"]["web_start"]
    assert f"loopora support --workdir {shlex.quote(str(workdir.resolve()))}" in payload["next_commands"]["support"]
    assert codex_status["next_commands"]["doctor"] == payload["next_commands"]["doctor"]
    assert codex_status["next_commands"]["web_start"] == payload["next_commands"]["web_start"]
    assert codex_status["next_commands"]["support"] == payload["next_commands"]["support"]
    assert codex_status["first_task_message_example"] == payload["first_task_message_example"]
    assert codex_status["first_task_message_example_state"] == payload["first_task_message_example_state"]
    assert codex_status["first_task_handoff_policy"] == payload["first_task_handoff_policy"]
    uninstall_response = client.post("/api/agent-adapters/codex/uninstall", json={"workdir": str(workdir)})
    uninstall_payload = uninstall_response.json()
    assert uninstall_response.status_code == HTTPStatus.OK
    assert uninstall_payload["next_commands"]["reinstall"].startswith(command_prefix)
    assert f"loopora init codex --workdir {shlex.quote(str(workdir.resolve()))}" in uninstall_payload["next_commands"]["reinstall"]
    assert uninstall_payload["next_actions"][0]["command"] == uninstall_payload["next_commands"]["reinstall"]
    assert uninstall_payload["next_action_kinds"] == ["reinstall_agent_entry", "refresh_agent_host"]
    assert uninstall_payload["next_action_ready_now_kinds"] == uninstall_payload["next_action_kinds"]
    assert uninstall_payload["next_action_ready_after_actions"] == {}


def test_agent_adapter_web_api_preserves_source_checkout_entry_in_copyable_commands(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "project with spaces"
    workdir.mkdir()
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    install_response = client.post("/api/agent-adapters/codex/install", json={"workdir": str(workdir)})
    install_payload = install_response.json()
    status_response = client.get("/api/agent-adapters", params={"workdir": str(workdir)})
    codex_status = next(item for item in status_response.json()["adapters"] if item["adapter"] == "codex")
    uninstall_response = client.post("/api/agent-adapters/codex/uninstall", json={"workdir": str(workdir)})
    uninstall_payload = uninstall_response.json()

    assert install_response.status_code == HTTPStatus.OK
    assert status_response.status_code == HTTPStatus.OK
    assert uninstall_response.status_code == HTTPStatus.OK
    for command in [
        install_payload["next_commands"]["doctor"],
        install_payload["next_commands"]["check"],
        install_payload["next_commands"]["agent_check"],
        install_payload["next_commands"]["web_start"],
        install_payload["next_commands"]["support"],
        install_payload["first_task_handoff_policy"]["fit_command"],
        codex_status["next_commands"]["doctor"],
        codex_status["next_commands"]["web_start"],
        codex_status["next_commands"]["support"],
        codex_status["first_task_handoff_policy"]["fit_command"],
        uninstall_payload["next_commands"]["reinstall"],
        uninstall_payload["next_actions"][0]["command"],
    ]:
        assert source_entry in command
        assert f"--workdir {shlex.quote(str(workdir.resolve()))}" in command
    for copy_rule in [
        install_payload["first_task_handoff_policy"]["copy_rule"],
        codex_status["first_task_handoff_policy"]["copy_rule"],
    ]:
        assert source_entry in copy_rule
        assert f"--workdir {shlex.quote(str(workdir.resolve()))}" in copy_rule
    assert uninstall_payload["next_actions"][0]["command"] == uninstall_payload["next_commands"]["reinstall"]


def test_agent_adapter_web_api_reports_invalid_json(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    invalid_json = client.post(
        "/api/agent-adapters/codex/install",
        content="{",
        headers={"content-type": "application/json"},
    )
    non_object = client.post("/api/agent-adapters/codex/uninstall", json=["not", "an", "object"])

    assert invalid_json.status_code == HTTPStatus.BAD_REQUEST
    assert "invalid JSON body" in invalid_json.json()["error"]
    assert non_object.status_code == HTTPStatus.BAD_REQUEST
    assert non_object.json()["error"] == "request body must be a JSON object"


def test_agent_adapter_web_api_requires_explicit_workdir_for_changes(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    install_without_workdir = client.post("/api/agent-adapters/codex/install", json={})
    uninstall_without_workdir = client.post("/api/agent-adapters/codex/uninstall", json={})
    uninstall_preview_without_workdir = client.post("/api/agent-adapters/codex/uninstall-preview", json={})
    install_with_blank_workdir = client.post("/api/agent-adapters/codex/install", json={"workdir": "   "})
    read_only_status = client.get("/api/agent-adapters")
    relative_read_only_status = client.get("/api/agent-adapters", params={"workdir": "."})
    relative_install = client.post("/api/agent-adapters/codex/install", json={"workdir": "."})

    assert read_only_status.status_code == HTTPStatus.OK
    read_only_payload = read_only_status.json()
    assert (read_only_payload["workdir"], read_only_payload["target_project_required"], read_only_payload["workdir_state"]["status"]) == ("", True, "required")
    assert [item["adapter"] for item in read_only_payload["adapters"]] == ["codex", "claude", "opencode"]
    assert all(item["status"] == "blocked_by_workdir" and item["workdir"] == "" for item in read_only_payload["adapters"])
    assert read_only_payload["next_actions"] == [
        {"kind": "choose_workdir", "command_ready": False, "command_blockers": ["target_project_required"]}
    ]
    read_only_text = json.dumps(read_only_payload, ensure_ascii=False)
    assert str(Path.cwd().resolve()) not in read_only_text
    assert "loopora init" not in read_only_text
    for response in (relative_read_only_status, relative_install):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert (payload["error"], payload["target_project_required"], payload["next_action_kind"]) == (
            "target_project_absolute_path_required", True, "choose_workdir",
        )
    for response, action, retry_kind in [
        (install_without_workdir, "install", "retry_install"),
        (uninstall_without_workdir, "uninstall", "retry_uninstall"),
        (uninstall_preview_without_workdir, "uninstall", "retry_uninstall"),
        (install_with_blank_workdir, "install", "retry_install"),
    ]:
        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert payload["loop_recovery"] == "adapter_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["action"] == action
        assert payload["workdir"] == ""
        assert payload["workdir_state"]["status"] == "required"
        assert payload["workdir_state"]["usable_for_agent_entries"] is False
        action_kinds = [item["kind"] for item in payload["next_actions"]]
        assert payload["adapter_workdir_recovery_summary"]["next_action_kinds"] == action_kinds == ["choose_workdir", retry_kind, "confirm_readiness"]
        assert "command" not in payload["next_actions"][1]
        assert "command" not in payload["next_actions"][2]
        assert payload["next_actions"][2]["after_action"] == retry_kind
    assert load_recent_workdirs() == []


def test_agent_adapter_web_api_explains_unusable_workdir_before_mutation(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing project"
    file_workdir = tmp_path / "not-a-project"
    file_workdir.write_text("not a directory\n", encoding="utf-8")

    missing_install = client.post("/api/agent-adapters/codex/install", json={"workdir": str(missing_workdir)})
    missing_uninstall = client.post("/api/agent-adapters/codex/uninstall", json={"workdir": str(missing_workdir)})
    file_install = client.post("/api/agent-adapters/codex/install", json={"workdir": str(file_workdir)})

    for response, action, retry_kind in (
        (missing_install, "install", "retry_install"),
        (missing_uninstall, "uninstall", "retry_uninstall"),
    ):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert payload["loop_recovery"] == "adapter_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["action"] == action
        assert payload["workdir"] == str(missing_workdir.resolve())
        assert payload["workdir_state"]["status"] == "missing"
        assert payload["workdir_state"]["usable_for_agent_entries"] is False
        assert payload["workdir_state"]["commands"]["create"] == f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}"
        action_kinds = [item["kind"] for item in payload["next_actions"]]
        assert payload["adapter_workdir_recovery_summary"]["next_action_kinds"] == action_kinds == [
            "create_workdir",
            retry_kind,
            "confirm_readiness",
        ]
        assert payload["next_actions"][2]["after_action"] == retry_kind
    assert not missing_workdir.exists()

    assert file_install.status_code == HTTPStatus.BAD_REQUEST
    file_payload = file_install.json()
    assert file_payload["loop_recovery"] == "adapter_workdir_unavailable"
    assert file_payload["status"] == "blocked_by_workdir"
    assert file_payload["workdir_state"]["status"] == "not_directory"
    assert file_payload["workdir_state"]["commands"] == {}
    file_action_kinds = [item["kind"] for item in file_payload["next_actions"]]
    assert file_payload["adapter_workdir_recovery_summary"]["next_action_kinds"] == file_action_kinds == [
        "choose_workdir",
        "retry_install",
        "confirm_readiness",
    ]
    assert file_payload["next_actions"][2]["after_action"] == "retry_install"
    assert file_workdir.read_text(encoding="utf-8") == "not a directory\n"
    assert load_recent_workdirs() == []


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

    monkeypatch.setattr(web_service_probe, "urlopen", lambda *_args, **_kwargs: FakeResponse(b'{"hello": true}'))
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742") is False

    monkeypatch.setattr(
        web_service_probe,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742") is True

    monkeypatch.setattr(
        web_service_probe,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"app_home": "/tmp/other-loopora", "running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742", expected_app_home="/tmp/current-loopora") is False

    monkeypatch.setattr(
        web_service_probe,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b'{"app_home": "/tmp/current-loopora", "running_count": 0, "queued_count": 0, "runs": []}'),
    )
    assert agent_web._loopora_web_responds("http://127.0.0.1:8742", expected_app_home="/tmp/current-loopora") is True


def test_web_service_probe_uses_configured_token_without_exposing_it(monkeypatch) -> None:
    seen: dict[str, object] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb) -> None:
            return None

        def read(self) -> bytes:
            return b'{"app_home":"/tmp/current-loopora","running_count":0,"queued_count":0,"runs":[]}'

    def fake_urlopen(request, *, timeout: float):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["accept"] = request.get_header("Accept")
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(web_service_probe, "urlopen", fake_urlopen)

    assert web_service_probe.loopora_web_responds(
        "http://127.0.0.1:8742/",
        expected_app_home="/tmp/current-loopora",
        auth_token="private-token",
    )
    assert seen == {
        "url": "http://127.0.0.1:8742/api/runtime/activity",
        "authorization": "Bearer private-token",
        "accept": "application/json",
        "timeout": 0.35,
    }


def test_configured_web_service_match_uses_current_app_home_and_auth(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}
    home = tmp_path / "loopora home"
    monkeypatch.setattr(local_web_service, "app_home", lambda: home)
    monkeypatch.setenv(APP_AUTH_ENV, "private-token")

    def responds(base_url: str, *, expected_app_home: str, auth_token: str) -> bool:
        seen.update(base_url=base_url, expected_app_home=expected_app_home, auth_token=auth_token)
        return True

    monkeypatch.setattr(local_web_service, "loopora_web_responds", responds)

    assert local_web_service.matching_configured_web_service("0.0.0.0", 9123)
    assert seen == {
        "base_url": "http://127.0.0.1:9123",
        "expected_app_home": str(home.resolve()),
        "auth_token": "private-token",
    }


def test_agent_web_discovery_reuses_only_matching_app_home(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    checked: list[tuple[str, str]] = []

    def responds(base_url: str, *, expected_app_home: str = "") -> bool:
        checked.append((base_url, expected_app_home))
        return base_url.endswith(":8743")

    monkeypatch.setattr(agent_web, "app_home", lambda: app_home)
    monkeypatch.setattr(agent_web, "_loopora_web_responds", responds)
    monkeypatch.setattr(agent_web, "_port_is_available", lambda _host, _port: False)

    result = agent_web.discover_local_web_service()

    assert result == {
        "status": "reused",
        "base_url": "http://127.0.0.1:8743",
        "reused": True,
        "started": False,
        "start_required": False,
        "start_available": True,
        "port": 8743,
    }
    assert checked == [
        ("http://127.0.0.1:8742", str(app_home.resolve())),
        ("http://127.0.0.1:8743", str(app_home.resolve())),
    ]


def test_agent_web_discovery_returns_foreground_start_target_without_starting(monkeypatch) -> None:
    monkeypatch.setattr(agent_web, "_loopora_web_responds", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(agent_web, "_port_is_available", lambda _host, port: port == 8744)

    result = agent_web.discover_local_web_service()

    assert result["status"] == "not_running"
    assert result["base_url"] == "http://127.0.0.1:8744"
    assert result["port"] == 8744
    assert result["reused"] is False
    assert result["started"] is False
    assert result["start_required"] is True
    assert result["start_available"] is True
    assert "foreground command" in str(result["warning"])
    assert "pid" not in result


def test_agent_web_discovery_uses_wider_port_preflight_and_can_report_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(agent_web, "_loopora_web_responds", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(agent_web, "_port_is_available", lambda *_args: False)
    monkeypatch.setattr(agent_web, "next_available_web_port", lambda **_kwargs: 9001)

    result = agent_web.discover_local_web_service()
    assert result["status"] == "not_running"
    assert result["port"] == 9001

    monkeypatch.setattr(agent_web, "next_available_web_port", lambda **_kwargs: None)
    result = agent_web.discover_local_web_service()
    assert result["status"] == "unavailable"
    assert result["start_available"] is False
    assert result["warning"] == "no available Loopora Web port was found"


def test_agent_web_discovery_has_no_process_ownership_capability() -> None:
    source = Path(agent_web.__file__).read_text(encoding="utf-8")

    for forbidden in ("subprocess", "Popen", "start_new_session", "AGENT_WEB_PID", "_start_web_process"):
        assert forbidden not in source
