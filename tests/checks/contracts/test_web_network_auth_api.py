from __future__ import annotations

import errno
import sqlite3
import json
import shlex
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from loopora import cli
from loopora import agent_adapter_command_prefix
from loopora.branding import APP_AUTH_ENV, APP_HOME_ENV
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION
import loopora.web as web_module
from loopora.service import LooporaError
from loopora.web import build_app


REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_serve_recovery_readiness(
    payload: dict,
    summary_key: str,
    *,
    expected: dict[str, object],
) -> None:
    expected = {
        "next_action_kinds": [action["kind"] for action in payload["next_actions"]],
        "next_action_ready_now_kinds": expected["ready_now"],
        "next_action_ready_after_actions": expected.get("ready_after", {}),
        "next_action_blocked_kinds": expected.get("blocked", []),
        "next_action_command_blockers": expected.get("blockers", {}),
    }
    assert {key: payload[key] for key in expected} == expected
    assert {key: payload[summary_key][key] for key in expected} == expected


def test_web_app_auth_middleware_has_dedicated_boundary() -> None:
    web_source = (REPO_ROOT / "src" / "loopora" / "web.py").read_text(encoding="utf-8")
    auth_source = (REPO_ROOT / "src" / "loopora" / "web_auth_middleware.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_auth_middleware import install_auth_middleware" in web_source
    assert "def install_auth_middleware" in auth_source
    assert "def _auth_token_matches" in auth_source
    assert "def _safe_internal_workdir_context" in auth_source
    assert "def _auth_token_matches" not in web_source
    assert "web_auth_middleware.py" in design_source


def test_web_app_refuses_remote_without_auth_or_explicit_unsafe_opt_in(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match=r"refusing to bind a non-loopback host without protection.*--auth-token '<token>'"):
        build_app(service=service, bind_host="0.0.0.0")

    app = build_app(service=service, bind_host="0.0.0.0", allow_unsafe_open=True)
    client = TestClient(app)
    response = client.get("/")

    assert app.state.access_state["auth_enabled"] is False
    assert app.state.access_state["remote_access_enabled"] is True
    assert app.state.access_state["native_dialogs_enabled"] is False
    assert response.status_code == HTTPStatus.OK


def test_cli_serve_json_remote_auth_gate_is_structured_before_app_start(monkeypatch, tmp_path: Path) -> None:
    def fail_bind_probe(*_args, **_kwargs) -> None:
        raise AssertionError("unprotected remote serve should fail before probing the bind target")

    def fail_build_app(**_kwargs):
        raise AssertionError("unprotected remote serve should fail before building Web")

    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", fail_bind_probe)
    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)

    runner = CliRunner()
    plain_result = runner.invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9761", "--workdir", str(tmp_path), "--language", "zh-CN"],
    )
    result = runner.invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9761", "--workdir", str(tmp_path), "--language", "zh", "--json"],
    )
    invalid = runner.invoke(cli.app, ["serve", "--workdir", str(tmp_path), "--language", "fr", "--json"])

    payload = json.loads(result.stdout)
    actions = payload["next_actions"]
    action_kinds = [action["kind"] for action in actions]
    assert result.exit_code == 1
    assert invalid.exit_code == 1
    assert json.loads(invalid.stdout)["error"].startswith("invalid --language: expected one of: en, zh")
    assert next(iter(payload)) == "serve_startup_recovery_summary"
    assert payload["serve_startup_recovery_summary"]["status"] == "blocked_by_network_auth"
    assert payload["serve_startup_recovery_summary"]["start_blocked_reason"] == "network_auth_required"
    assert payload["serve_startup_recovery_summary"]["next_action_kinds"] == action_kinds
    _assert_serve_recovery_readiness(payload, "serve_startup_recovery_summary", expected={"ready_now": action_kinds})
    assert action_kinds == ["configure_auth_token", "use_loopback_web", "allow_unsafe_open"]
    assert "--auth-token '<token>'" in actions[0]["command"]
    assert "--host 127.0.0.1" in actions[1]["command"]
    assert "--allow-unsafe-open" in actions[2]["command"]
    assert plain_result.exit_code == 1
    assert "Loopora Web 启动受阻" in plain_result.stderr
    assert "原因：网络访问需要认证" in plain_result.stderr
    assert "配置 auth token" in plain_result.stderr
    assert "使用 loopback Web" in plain_result.stderr
    assert "显式 unsafe opt-in" in plain_result.stderr
    assert "--auth-token '<token>'" in plain_result.stderr
    assert "--host 127.0.0.1" in plain_result.stderr
    assert "--allow-unsafe-open" in plain_result.stderr
    assert plain_result.stderr.count("--language zh") == 3
    assert "Retry with an auth token" not in plain_result.stderr
    assert "language" not in payload
    assert "--language" not in result.stdout
    assert "Loopora Web:" not in result.output


def test_cli_serve_blocks_future_app_database_before_web_start(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "loopora.cli_serve_commands.build_app", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("future App DB must block before Web start"))
    )
    result = CliRunner().invoke(cli.app, ["serve", "--workdir", str(workdir), "--port", "9762", "--json"])
    doctor = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", "9762", "--json"])
    payload = json.loads(result.stdout)
    doctor_payload = json.loads(doctor.stdout)
    assert (
        result.exit_code,
        payload["serve_startup_recovery_summary"]["status"],
        payload["start_blocked_reason"],
        payload["app_state"]["status"],
        payload["app_state"]["web_ready"],
    ) == (1, "blocked_by_app_state", "app_state_not_ready", "future_version", False)
    assert payload["readiness_blockers"] == [
        {"kind": "app_state_not_ready", "status": "future_version", "recovery_action": "use_matching_loopora_version_or_reset"}
    ]
    assert [item["kind"] for item in payload["next_actions"][:4]] == [
        "create_recovery_archive",
        "use_matching_loopora_version_or_reset",
        "retry_web_start",
        "use_temporary_app_home",
    ]
    assert payload["next_actions"][0]["private_content"] is True
    assert payload["next_actions"][1]["after_action"] == "create_recovery_archive"
    assert (payload["next_actions"][2]["command_ready"], "matching or newer Loopora version" in payload["error"]) == (False, True)
    _assert_serve_recovery_readiness(
        payload,
        "serve_startup_recovery_summary",
        expected={
            "ready_now": ["create_recovery_archive", "use_temporary_app_home"],
            "ready_after": {"use_matching_loopora_version_or_reset": "create_recovery_archive"},
            "blocked": ["retry_web_start"],
            "blockers": {"retry_web_start": ["app_state_not_ready"]},
        },
    )
    assert (doctor.exit_code, doctor_payload["diagnose_doctor_summary"]["app_state_web_ready"], doctor_payload["web"]["readiness_blockers"][0]["status"]) == (
        1,
        False,
        "future_version",
    )
    assert any("matching or newer Loopora version" in step for step in doctor_payload["next_steps"])


@pytest.mark.parametrize(
    ("path_kind", "expected_state", "expected_action"),
    [
        ("missing", "missing", "Create the target project directory"),
        ("file", "not_directory", "Choose an existing project directory"),
    ],
)
def test_cli_serve_workdir_recovery_uses_product_path_before_web_start(
    monkeypatch,
    tmp_path: Path,
    path_kind: str,
    expected_state: str,
    expected_action: str,
) -> None:
    target = tmp_path / "not a project"
    if path_kind == "file":
        target.write_text("not a directory\n", encoding="utf-8")
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/.venv/bin/loopora"])

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building Web for an unusable target project")

    def fail_uvicorn_run(_app, **_kwargs) -> None:
        raise AssertionError("serve should fail before starting Web for an unusable target project")

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fail_uvicorn_run)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "127.0.0.1", "--port", "9761", "--workdir", str(target)],
    )
    json_result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "127.0.0.1", "--port", "9761", "--workdir", str(target), "--json"],
    )

    output = result.output
    assert result.exit_code == 1
    assert "Invalid value for '--workdir'" not in output
    assert "Loopora Web start is blocked" in output
    assert f"project directory state: {expected_state}" in output
    assert expected_action in output
    assert "Confirm readiness after the target is usable" in output
    assert "Retry Web start" in output
    if path_kind == "missing":
        quoted_target = shlex.quote(str(target.resolve(strict=False)))
        source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
        assert f"mkdir -p {quoted_target}" in output
        assert f"{source_entry} doctor --workdir {quoted_target} --web-host 127.0.0.1 --web-port 9761" in output
        assert f"{source_entry} serve --open --host 127.0.0.1 --port 9761 --workdir {quoted_target}" in output
        assert not target.exists()
    else:
        assert "mkdir -p" not in output
    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    first_kind = "create_workdir" if path_kind == "missing" else "choose_workdir"
    assert next(iter(payload)) == "serve_workdir_recovery_summary"
    assert payload["serve_workdir_recovery_summary"]["next_action_kinds"] == action_kinds == [first_kind, "confirm_readiness", "retry_web_start"]
    assert payload["serve_workdir_recovery_summary"]["workdir_state_status"] == expected_state
    assert payload["serve_workdir_recovery_summary"]["network_auth_required"] is False
    _assert_serve_recovery_readiness(
        payload,
        "serve_workdir_recovery_summary",
        expected={"ready_now": [first_kind], "ready_after": {"confirm_readiness": first_kind, "retry_web_start": first_kind}},
    )


def test_cli_serve_workdir_recovery_keeps_network_auth_visible_before_web_start(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "missing project"

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building Web for an unusable target project")

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9761", "--workdir", str(target)],
    )
    json_result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9761", "--workdir", str(target), "--json"],
    )

    output = result.output
    assert result.exit_code == 1
    assert "project directory state: missing" in output
    assert "network auth:" in output
    assert "--auth-token or LOOPORA_AUTH_TOKEN" in output
    assert "refusing to bind a non-loopback host" not in output
    assert json_result.exit_code == 1
    json_payload = json.loads(json_result.stdout)
    assert json_payload["serve_workdir_recovery_summary"]["network_auth_required"] is True
    assert "--auth-token or LOOPORA_AUTH_TOKEN" in json_payload["network_auth_note"]


@pytest.mark.parametrize(
    ("port", "expected_error"),
    [
        ("0", "invalid --port: must be between 1 and 65535"),
        ("70000", "invalid --port: must be between 1 and 65535"),
        ("nope", "invalid --port: must be an integer between 1 and 65535"),
    ],
)
def test_cli_serve_port_errors_are_product_validation_before_web_start(
    monkeypatch,
    tmp_path: Path,
    port: str,
    expected_error: str,
) -> None:
    def fail_bind_probe(*_args, **_kwargs) -> None:
        raise AssertionError("serve should validate port before probing the bind target")

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should validate port before building Web")

    def fail_uvicorn_run(_app, **_kwargs) -> None:
        raise AssertionError("serve should validate port before starting Web")

    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", fail_bind_probe)
    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fail_uvicorn_run)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "127.0.0.1", "--port", port, "--workdir", str(tmp_path)],
    )
    json_result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "127.0.0.1", "--port", port, "--workdir", str(tmp_path), "--json"],
    )

    output = result.output
    assert result.exit_code == 2
    assert expected_error in output
    assert "Invalid value" not in output
    assert "Usage:" not in output
    assert "Loopora Web:" not in output
    assert json_result.exit_code == 2
    payload = json.loads(json_result.stdout)
    assert payload["error"] == expected_error
    assert payload["serve_startup_error_summary"]["start_blocked_reason"] == "invalid_port"
    assert payload["serve_startup_error_summary"]["next_action_kinds"] == ["choose_valid_port"]
    assert payload["next_actions"][0]["kind"] == "choose_valid_port"
    _assert_serve_recovery_readiness(payload, "serve_startup_error_summary", expected={"ready_now": ["choose_valid_port"]})


def test_cli_serve_port_conflict_recovery_preserves_workdir_and_auth_without_printing_token(
    monkeypatch,
    tmp_path: Path,
) -> None:
    secret_token = "local-secret-token"

    def fail_bind_probe(*_args, **_kwargs) -> None:
        raise OSError(errno.EADDRINUSE, "port already in use")

    def next_port(*, host: str, port: int) -> int:
        assert host == "127.0.0.1"
        return port + 1

    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", fail_bind_probe)
    monkeypatch.setattr("loopora.cli_serve_output.next_available_web_port", next_port)
    monkeypatch.setattr(
        "loopora.cli_serve_commands.build_app",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("serve should fail before building Web")),
    )
    serve_args = ["serve", "--host", "127.0.0.1", "--port", "9762", "--auth-token", secret_token, "--workdir", str(tmp_path)]

    result = CliRunner().invoke(cli.app, serve_args)
    json_result = CliRunner().invoke(cli.app, [*serve_args, "--json"])

    assert result.exit_code == 1
    assert "cannot start Loopora Web on http://127.0.0.1:9762" in result.output
    assert "Try `" in result.output
    assert "--port 9763" in result.output
    assert "--auth-token '<token>'" in result.output
    assert f"--workdir {shlex.quote(str(tmp_path))}" in result.output
    assert secret_token not in result.output
    payload = json.loads(json_result.stdout)
    action_kinds = [action["kind"] for action in payload["next_actions"]]
    assert json_result.exit_code == 1
    assert payload["serve_startup_recovery_summary"]["status"] == "blocked_by_port_conflict"
    assert payload["serve_startup_recovery_summary"]["start_blocked_reason"] == "port_in_use"
    assert payload["serve_startup_recovery_summary"]["next_action_kinds"] == action_kinds
    assert action_kinds == ["retry_web_start_on_alternate_port", "stop_existing_service", "choose_web_port"]
    _assert_serve_recovery_readiness(payload, "serve_startup_recovery_summary", expected={"ready_now": action_kinds})
    assert "--port 9763" in payload["next_actions"][0]["command"]
    assert "--auth-token '<token>'" in payload["next_actions"][0]["command"]
    assert secret_token not in json_result.stdout
    monkeypatch.setattr("loopora.cli_serve_output.next_available_web_port", lambda **_kwargs: None)
    no_alternate = CliRunner().invoke(cli.app, [*serve_args, "--json"])
    no_alternate_payload = json.loads(no_alternate.stdout)
    assert [action["kind"] for action in no_alternate_payload["next_actions"]] == ["stop_existing_service", "choose_web_port"]
    assert "retry_web_start_on_alternate_port" not in no_alternate.stdout


def test_cli_serve_json_bind_failure_is_structured_and_redacted_before_app_start(monkeypatch) -> None:
    def fail_probe_web_bind(_host: str, _port: int) -> None:
        raise OSError("permission denied: /private/socket")

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building the app when bind preflight fails")

    def fail_uvicorn_run(_app, **_kwargs) -> None:
        raise AssertionError("serve should fail before starting uvicorn when bind preflight fails")

    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", fail_probe_web_bind)
    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fail_uvicorn_run)

    result = CliRunner().invoke(cli.app, ["serve", "--host", "127.0.0.1", "--port", "9755", "--json"])

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["serve_startup_recovery_summary"]["status"] == "blocked_by_bind"
    assert payload["serve_startup_recovery_summary"]["start_blocked_reason"] == "bind_failed"
    assert payload["serve_startup_recovery_summary"]["next_action_kinds"] == ["resolve_web_bind"]
    assert payload["next_actions"][0]["kind"] == "resolve_web_bind"
    _assert_serve_recovery_readiness(payload, "serve_startup_recovery_summary", expected={"ready_now": ["resolve_web_bind"]})
    assert "Choose a different --host / --port" in payload["next_actions"][0]["note"]
    assert "permission denied" not in result.stdout
    assert "/private/socket" not in result.stdout
    assert "Loopora Web:" not in result.output


def test_cli_doctor_loopback_auth_summary_matches_configured_web_start(tmp_path: Path) -> None:
    secret_token = "local-doctor-token"
    env = {
        APP_AUTH_ENV: secret_token,
        APP_HOME_ENV: str(tmp_path / "app-home"),
    }
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", "9764", "--json"],
        env=env,
    )
    plain = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", "9764"],
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["web"]["loopback"] is True
    assert payload["web"]["auth_required"] is False
    assert payload["web"]["auth_enabled"] is True
    assert payload["web"]["auth_token_configured"] is True
    assert payload["web"]["auth_token_printed"] is False
    assert secret_token not in result.stdout
    assert secret_token not in plain.stdout
    assert "web: http://127.0.0.1:9764 (auth token configured)" in plain.stdout
    assert "web auth: LOOPORA_AUTH_TOKEN is configured in this shell; keep it set when running web start." in plain.stdout
    assert "loopback local default" not in plain.stdout


def test_web_doctor_api_uses_running_service_auth_state_without_public_token_status(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    secret_token = "running-web-token"
    client = TestClient(
        build_app(
            service=service,
            bind_host="127.0.0.1",
            bind_port=9765,
            auth_token=secret_token,
        )
    )

    response = client.get(
        "/api/diagnostics/doctor",
        params={"workdir": str(tmp_path)},
        headers={"Authorization": f"Bearer {secret_token}"},
    )
    public = client.get(
        "/api/diagnostics/doctor",
        params={"workdir": str(tmp_path), "public": "true"},
        headers={"Authorization": f"Bearer {secret_token}"},
    )

    payload = response.json()
    assert response.status_code == HTTPStatus.OK
    assert payload["web"]["already_running"] is True
    assert payload["web"]["loopback"] is True
    assert payload["web"]["auth_required"] is False
    assert payload["web"]["auth_enabled"] is True
    assert payload["web"]["auth_token_configured"] is True
    assert f"--workdir {tmp_path}" in payload["commands"]["confirm_readiness"]
    assert "--web-port 9765" in payload["commands"]["confirm_readiness"]
    assert secret_token not in response.text

    public_text = public.text
    assert public.status_code == HTTPStatus.OK
    assert "auth_enabled" not in public_text
    assert "auth_token_configured" not in public_text
    assert '"commands"' not in public_text
    assert "9765" not in public_text
    assert secret_token not in public_text


def test_web_app_refuses_unprotected_remote_before_service_initialization(monkeypatch) -> None:
    def fail_create_service():
        raise AssertionError("unprotected remote build must fail before service creation")

    monkeypatch.setattr(web_module, "create_service", fail_create_service)

    with pytest.raises(LooporaError, match="refusing to bind a non-loopback host without protection"):
        build_app(bind_host="0.0.0.0")


def test_network_mode_requires_auth_token_and_sets_cookie(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/")
    assert unauthorized.status_code == HTTPStatus.UNAUTHORIZED
    assert "Auth token required" in unauthorized.text
    assert 'data-testid="auth-token-form"' in unauthorized.text
    assert 'name="return_to" value="/"' in unauthorized.text
    assert "?token=&lt;your-token&gt;" not in unauthorized.text

    unsupported_header = client.get("/", headers={"X-Other-Token": "secret-token"})
    assert unsupported_header.status_code == HTTPStatus.UNAUTHORIZED

    bearer_authorized = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")).get(
        "/api/loops",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert bearer_authorized.status_code == HTTPStatus.OK

    custom_header_authorized = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")).get(
        "/api/loops",
        headers={"X-Loopora-Token": "secret-token"},
    )
    assert custom_header_authorized.status_code == HTTPStatus.OK

    authorized = client.get("/?token=secret-token", follow_redirects=False)
    assert authorized.status_code == HTTPStatus.SEE_OTHER
    assert authorized.headers["location"] == "/"
    assert "secret-token" not in authorized.headers["location"]
    assert client.cookies.get("loopora_auth") == "secret-token"

    api_response = client.get("/api/loops")
    assert api_response.status_code == HTTPStatus.OK


def test_internal_error_support_link_preserves_safe_return_context(service_factory) -> None:
    app = build_app(service=service_factory(scenario="success"))

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom?token=secret-token&workdir=/tmp/demo")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert 'data-testid="web-error-page"' in response.text
    assert ('href="/support?workdir=%2Ftmp%2Fdemo&amp;return_to=%2Fboom%3Fworkdir%3D%252Ftmp%252Fdemo" data-testid="web-error-support-link"') in response.text
    assert "secret-token" not in response.text


def test_network_mode_query_token_redirects_human_pages_without_breaking_api(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    page_response = client.get("/loops/new?token=secret-token&workdir=/tmp/demo", follow_redirects=False)
    assert page_response.status_code == HTTPStatus.SEE_OTHER
    assert page_response.headers["location"] == "/loops/new?workdir=%2Ftmp%2Fdemo"
    assert "secret-token" not in page_response.headers["location"]
    assert client.cookies.get("loopora_auth") == "secret-token"

    api_client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))
    api_response = api_client.get("/api/loops?token=secret-token", follow_redirects=False)
    assert api_response.status_code == HTTPStatus.OK
    assert api_response.headers.get("location") is None


def test_network_mode_strips_sensitive_query_keys_case_insensitively(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    login = client.post("/auth/token", data={"token": "secret-token", "return_to": "/"}, follow_redirects=False)
    assert login.status_code == HTTPStatus.SEE_OTHER
    assert client.cookies.get("loopora_auth") == "secret-token"

    response = client.get("/loops/new?Token=secret-token&workdir=/tmp/demo", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == "/loops/new?workdir=%2Ftmp%2Fdemo"
    assert "Token=" not in response.headers["location"]
    assert "secret-token" not in response.headers["location"]


def test_network_mode_strips_nested_return_tokens_after_auth_without_redirecting_plain_context(
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))
    login = client.post("/auth/token", data={"token": "secret-token", "return_to": "/"}, follow_redirects=False)
    assert login.status_code == HTTPStatus.SEE_OTHER

    plain_context = client.get("/loops/new?workdir=/tmp/demo", follow_redirects=False)

    assert plain_context.status_code == HTTPStatus.OK
    assert plain_context.headers.get("location") is None

    nested_return_to = quote(
        "/loops/new/manual?workdir=/tmp/demo&access_token=secret-token#token=secret-token&section=manual",
        safe="",
    )
    response = client.get(f"/roles?return_to={nested_return_to}&panel=custom", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == ("/roles?return_to=%2Floops%2Fnew%2Fmanual%3Fworkdir%3D%252Ftmp%252Fdemo%23section%3Dmanual&panel=custom")
    assert "secret-token" not in response.headers["location"]
    assert "access_token" not in response.headers["location"]
    assert "token=" not in response.headers["location"]

    api_response = client.get(f"/api/loops?return_to={nested_return_to}", follow_redirects=False)

    assert api_response.status_code == HTTPStatus.OK
    assert api_response.headers.get("location") is None


@pytest.mark.parametrize(
    ("path", "location"),
    [
        ("/loops/new", "/loops/new?workdir=%2Ftmp%2Fdemo"),
        ("/loops/new/bundle", "/loops/new/bundle?workdir=%2Ftmp%2Fdemo"),
        ("/loops/new/manual", "/loops/new/manual?workdir=%2Ftmp%2Fdemo"),
    ],
)
def test_create_pages_redirect_strip_sensitive_query_keys_without_auth(service_factory, path: str, location: str) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get(f"{path}?Token=secret-token&workdir=/tmp/demo", follow_redirects=False)

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == location
    assert "Token=" not in response.headers["location"]
    assert "secret-token" not in response.headers["location"]


def test_network_mode_auth_form_sets_cookie_and_strips_return_token(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    blocked = client.get("/loops/new?access_token=wrong-token&workdir=/tmp/demo", follow_redirects=False)
    assert blocked.status_code == HTTPStatus.UNAUTHORIZED
    assert 'name="return_to" value="/loops/new?workdir=%2Ftmp%2Fdemo"' in blocked.text
    assert "wrong-token" not in blocked.text

    invalid = client.post(
        "/auth/token",
        data={"token": "wrong-token", "return_to": "/loops/new?access_token=secret-token&workdir=/tmp/demo"},
        follow_redirects=False,
    )
    assert invalid.status_code == HTTPStatus.UNAUTHORIZED
    assert 'data-testid="auth-token-error"' in invalid.text
    assert client.cookies.get("loopora_auth") is None
    assert "secret-token" not in invalid.text

    authorized = client.post(
        "/auth/token",
        data={"token": "secret-token", "return_to": "/loops/new?access_token=secret-token&workdir=/tmp/demo"},
        follow_redirects=False,
    )
    assert authorized.status_code == HTTPStatus.SEE_OTHER
    assert authorized.headers["location"] == "/loops/new?workdir=%2Ftmp%2Fdemo"
    assert "secret-token" not in authorized.headers["location"]
    assert client.cookies.get("loopora_auth") == "secret-token"


def test_network_mode_auth_json_hint_prefers_form_and_header(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/", headers={"accept": "Application/JSON"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["hint"] == "open the auth form or send Authorization: Bearer <your-token>"
    assert "?token=<your-token>" not in response.text


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


def test_network_mode_alignment_page_explains_server_side_paths(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/loops/new/bundle", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="alignment-workdir-panel"' in response.text
    assert 'data-testid="alignment-remote-path-note"' in response.text
    assert "absolute project path from the server machine" in response.text


def test_network_mode_manual_loop_page_hides_native_browse_controls(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/loops/new/manual", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="manual-workdir-remote-path-note"' in response.text
    assert 'data-testid="manual-spec-remote-path-note"' in response.text
    assert 'data-testid="workdir-browse-button"' not in response.text
    assert 'id="browse-spec"' not in response.text
    assert "absolute project path from the server machine" in response.text
    assert "absolute spec file path from the server machine" in response.text


def test_network_mode_plan_file_source_actions_are_copy_only(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    bundles_response = client.get("/bundles", headers={"Authorization": "Bearer secret-token"})
    manual_response = client.get("/loops/new/manual", headers={"Authorization": "Bearer secret-token"})
    alignment_response = client.get("/loops/new/bundle", headers={"Authorization": "Bearer secret-token"})

    for response in (bundles_response, manual_response, alignment_response):
        assert response.status_code == HTTPStatus.OK
        assert 'data-testid="alignment-source-open-button"' in response.text
        assert 'data-path-action-mode="copy"' in response.text
        assert "Copy source path" in response.text


def test_network_mode_run_detail_trace_paths_are_copy_only(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Remote Trace Path Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=1,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get(f"/runs/{run['id']}", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="takeaway-open-build"' in response.text
    assert 'data-testid="takeaway-open-logs"' in response.text
    assert 'data-path-action-mode="copy"' in response.text
    assert 'aria-disabled="true"' not in response.text
    assert "Copy workdir path" in response.text
    assert "Copy .loopora logs path" in response.text
