from __future__ import annotations

import json
import logging
from pathlib import Path
import socket
import sqlite3

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from loopora import cli
from loopora.branding import APP_HOME_ENV
from loopora.diagnose_doctor import doctor_public_json_payload
from loopora.diagnostics import LooporaJsonFormatter, get_logger, log_exception
from loopora.event_redaction import redact_sensitive_text
from loopora.settings import app_home, configure_logging
from loopora.web import build_app


EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT = 15
ROOT = Path(__file__).resolve().parents[3]


def _read_service_log_records() -> list[dict]:
    log_path = app_home() / "logs" / "service.log"
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_api_doctor_public_report_omits_local_paths_and_commands(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="127.0.0.1", bind_port=9123))

    response = client.get("/api/diagnostics/doctor", params={"workdir": str(sample_workdir), "public": "true"})
    payload = response.json()
    encoded = str(payload)
    assert response.status_code == 200
    assert payload["schema_version"] == 2
    assert payload["diagnose_doctor_public_summary"]["schema_version"] == 2
    assert payload["diagnose_doctor_public_summary"]["redacted"] is True
    assert payload["redacted"] is True
    assert payload["diagnose_doctor_public_summary"]["environment"] == payload["environment"]
    assert payload["environment"]["python"] == payload["package"]["python"]
    assert payload["environment"]["os"]
    assert payload["package"]["source_revision"]
    assert payload["package"]["source_tree_status"] in {"clean", "dirty", "unknown"}
    assert payload["status"] == "not_ready"
    assert payload["agent_entry_ready"] is False
    assert payload["strict_ready"] is False
    assert payload["diagnose_doctor_public_summary"]["agent_entry_ready"] is False
    assert payload["diagnose_doctor_public_summary"]["strict_ready"] is False
    assert payload["project_directory_status"] == "ready"
    assert payload["diagnose_doctor_public_summary"]["project_directory_status"] == "ready"
    assert payload["diagnose_doctor_public_summary"]["first_task_guidance_available"] is True
    assert (payload["first_task_guidance_available"], payload["first_task_message_example_state"]["copy_allowed"]) == (True, False)
    assert payload["app_state"]["status"] == "not_initialized"
    assert payload["web"]["recovery_action"] == "start_web_after_readiness"
    assert payload["web"]["alternate_port_available"] is False
    assert payload["diagnose_doctor_public_summary"]["web_recovery_action"] == "start_web_after_readiness"
    assert (
        payload["next_action_kinds"]
        == payload["next_actions"]
        == [
            "check_fit_first",
            "install_agent_entry",
            "confirm_readiness",
            "run_loopora_plan",
            "support",
        ]
    )
    assert payload["primary_next_action_kind"] == payload["diagnose_doctor_public_summary"]["primary_next_action_kind"] == "check_fit_first"
    assert [item["kind"] for item in payload["next_action_summaries"]] == payload["next_action_kinds"]
    assert payload["diagnose_doctor_public_summary"]["next_action_kinds"] == payload["next_action_kinds"]
    assert payload["diagnose_doctor_public_summary"]["next_action_summaries"] == payload["next_action_summaries"]
    assert (
        "static fit guide" in payload["next_action_summaries"][0]["summary"],
        "same-Agent project entry that matches the current host" in payload["next_action_summaries"][1]["summary"],
        "After installing the matching same-Agent project entry" in payload["next_action_summaries"][2]["summary"],
    ) == (True, True, True)
    assert any(item["adapter"] == "codex" and item["next_action"] == "install_agent_entry" for item in payload["agent_entries"])
    assert str(sample_workdir) not in encoded
    assert "workdir" not in encoded
    assert "commands" not in encoded
    assert "loopora doctor" not in encoded
    assert "/loopora-plan" not in encoded
    assert '"first_task_message_example"' not in encoded
    assert "python_executable" not in encoded
    assert "db_path" not in encoded


def test_doctor_public_report_fallback_uses_stable_action_kind_taxonomy() -> None:
    payload = doctor_public_json_payload(
        {
            "schema_version": 2,
            "status": "not_ready",
            "ready": False,
            "agent_entry_ready": False,
            "strict_ready": False,
            "package": {},
            "app_state": {"web_ready": True},
            "web": {"start_available": True},
            "workdir_state": {"status": "ready"},
            "agent_entries": [{"adapter": "codex", "ready": False, "next_action": "install_agent_entry"}],
            "next_action_items": [],
        }
    )

    assert payload["next_actions"] == ["check_fit_first", "install_agent_entry", "confirm_readiness", "run_loopora_plan", "support"]
    assert [item["kind"] for item in payload["next_action_summaries"]] == payload["next_actions"]
    assert "install_one_agent_entry" not in json.dumps(payload, ensure_ascii=False)

    for status, expected in (
        ("missing", ["create_project_directory", "confirm_readiness", "support"]),
        ("not_directory", ["choose_project_directory", "confirm_readiness", "support"]),
        ("unavailable", ["choose_project_directory", "confirm_readiness", "support"]),
    ):
        blocked_payload = doctor_public_json_payload(
            {
                "schema_version": 2,
                "status": "not_ready",
                "ready": False,
                "agent_entry_ready": False,
                "strict_ready": False,
                "package": {},
                "app_state": {"web_ready": False},
                "web": {"start_available": True},
                "workdir_state": {"status": status},
                "agent_entries": [{"adapter": "codex", "ready": False, "next_action": "install_agent_entry"}],
                "next_action_items": [],
            }
        )

        assert blocked_payload["next_actions"] == expected
        assert "install_agent_entry" not in blocked_payload["next_actions"]


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
        "TOKEN_SECRET_MARKER",
        "CONTEXT_TOKEN_SECRET_MARKER",
        "HEADER_SECRET_MARKER",
        "COOKIE_SECRET_MARKER",
        "PRIVATE_KEY_SECRET_MARKER",
        "NESTED_PRIVATE_KEY_SECRET_MARKER",
        "ACCESS_TOKEN_SECRET_MARKER",
        "BEARER_TOKEN_SECRET_MARKER",
        "CLIENT_SECRET_MARKER",
        "ERROR_SECRET_MARKER",
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
        "MESSAGE_SECRET_MARKER",
        "WORKDIR_SECRET_MARKER",
        "CONTEXT_TOKEN_SECRET_MARKER",
        "HEADER_SECRET_MARKER",
        "COOKIE_SECRET_MARKER",
        "REFRESH_TOKEN_SECRET_MARKER",
        "NESTED_SECRET_MARKER",
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
        "PRIVATE_KEY_SECRET_MARKER",
        "CLIENT_SECRET_MARKER",
        "X_API_KEY_SECRET_MARKER",
        "LOOPORA_TOKEN_SECRET_MARKER",
        "ACCESS_TOKEN_FLAG_SECRET_MARKER",
        "REFRESH_TOKEN_FLAG_SECRET_MARKER",
        "ID_TOKEN_FLAG_SECRET_MARKER",
        "SESSION_TOKEN_FLAG_SECRET_MARKER",
        "PROXY_AUTH_FLAG_SECRET_MARKER",
        "SET_COOKIE_FLAG_SECRET_MARKER",
        "COOKIE_FLAG_SECRET_MARKER",
        "AUTHORIZATION_FLAG_SECRET_MARKER",
        "ENV_PRIVATE_KEY_SECRET_MARKER",
        "ENV_CLIENT_SECRET_MARKER",
        "PROXY_AUTH_SECRET_MARKER",
    )
    assert redacted.count("<secret omitted>") == EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT


def test_doctor_chinese_plain_surface_and_next_commands_share_language(monkeypatch, tmp_path: Path) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    port = _free_local_port()
    invocations = (
        ["doctor", "--workdir", str(project), "--web-port", str(port), "--language", "zh-CN"],
        ["diagnose", "doctor", "--workdir", str(project), "--web-port", str(port), "--language", "中文"],
    )

    for args in invocations:
        result = CliRunner().invoke(cli.app, args)
        assert result.exit_code == 1, result.stdout
        assert all(
            term in result.stdout
            for term in (
                "Loopora Doctor：未就绪",
                "同一 Agent 项目入口就绪：否",
                "就绪摘要：",
                "首要下一步：",
                "同一 Agent 项目入口：",
                "下一步：",
                "首次任务消息交接：",
            )
        )
        assert all(term not in result.stdout for term in ("readiness summary:", "primary next action:", "first task message handoff:"))
        assert all(term in result.stdout for term in ("doctor --workdir", "fit --workdir", "support --workdir", "--language zh"))
        assert all(f"init {adapter} --workdir" in result.stdout and f"init {adapter} --workdir {project} --language zh" in result.stdout for adapter in ("codex", "claude", "opencode"))
        assert all("--language zh" in line for line in result.stdout.splitlines() if "loopora serve" in line)


def test_doctor_language_does_not_change_private_or_public_json_contract(monkeypatch, tmp_path: Path) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    port = str(_free_local_port())
    private = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(project), "--web-port", port, "--language", "zh", "--json"])
    public = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(project), "--web-port", port, "--language", "zh", "--public-json"])
    private_payload, public_payload = json.loads(private.stdout), json.loads(public.stdout)

    assert (private.exit_code, public.exit_code) == (1, 1)
    assert private_payload["primary_next_action_kind"] == public_payload["primary_next_action_kind"] == "check_fit_first"
    assert private_payload["next_action_kinds"] == public_payload["next_action_kinds"] == [
        "check_fit_first",
        "install_agent_entry",
        "confirm_readiness",
        "run_loopora_plan",
        "support",
    ]
    assert all("language" not in payload for payload in (private_payload, public_payload))
    assert "commands" not in json.dumps(public_payload, ensure_ascii=False)


def test_doctor_chinese_recovery_and_source_checkout_keep_the_safe_primary(monkeypatch, tmp_path: Path) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    with sqlite3.connect(home / "app.db") as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 1")

    recovery = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(project), "--language", "zh"])
    monkeypatch.chdir(ROOT)
    source_checkout = CliRunner().invoke(cli.app, ["doctor", "--language", "zh"])

    assert recovery.exit_code == 1, recovery.stdout
    assert "首要下一步：删除有价值的本地历史前，先创建并审查私有精确路径恢复归档" in recovery.stdout
    assert "App 状态：需要开发重置" in recovery.stdout
    assert all(fragment in recovery.stdout for fragment in ("recovery create --workdir", "dev reset --scope app --workdir", "--yes --language zh"))
    assert recovery.stdout.count("--language zh") >= 6
    assert "重置前私有恢复归档：" in recovery.stdout
    assert source_checkout.exit_code == 1, source_checkout.stdout
    assert "Loopora Doctor：需要目标项目" in source_checkout.stdout
    assert all(
        command in source_checkout.stdout
        for command in (
            'doctor --workdir "$PWD" --language zh',
            'fit --workdir "$PWD" --language zh',
            'support --workdir "$PWD" --language zh',
        )
    )


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _assert_markers_omitted(text: str, *markers: str) -> None:
    for marker in markers:
        assert marker not in text
