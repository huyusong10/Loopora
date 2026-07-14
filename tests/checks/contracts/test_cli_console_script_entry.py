from __future__ import annotations

import errno
import json
import re
import socket
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli, web_bind_preflight
from loopora.diagnose_doctor import package_identity_report, package_source_label

from cli_first_use_docs_test_support import assert_fit_unreviewed_plain_hides_routes, complete_fit_review_cli_args, result_error_text

MODULE_HELP_TIMEOUT_SECONDS = 10
CLI_SUCCESS = 0
ROOT = Path(__file__).resolve().parents[3]


def test_cli_package_exposes_loopora_console_script() -> None:
    console_scripts = {entry_point.name: entry_point.value for entry_point in distribution("loopora").entry_points if entry_point.group == "console_scripts"}

    assert console_scripts["loopora"] == "loopora.cli:app"


def test_cli_serve_command_registration_lives_in_serve_boundary() -> None:
    root_source = (ROOT / "src" / "loopora" / "cli_root_commands.py").read_text(encoding="utf-8")
    serve_source = (ROOT / "src" / "loopora" / "cli_serve_commands.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_serve_commands import register_serve_command" in root_source
    assert "def _register_serve_command" not in root_source
    assert "build_app(" not in root_source
    assert "uvicorn.run" not in root_source
    assert "AllowUnsafeOpenOption" not in root_source
    assert "def register_serve_command" in serve_source
    assert "build_app(" in serve_source
    assert "uvicorn.run" in serve_source
    assert "SERVE_HELP_EPILOG" in serve_source
    assert "serve command registration" in service_boundaries
    assert "cli_serve_commands.py" in contracts


def test_cli_package_exposes_python_module_entry_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "loopora", "--help"],
        capture_output=True,
        check=False,
        text=True,
        timeout=MODULE_HELP_TIMEOUT_SECONDS,
    )

    assert result.returncode == CLI_SUCCESS
    assert "Loopora CLI" in result.stdout
    assert "init" in result.stdout


def test_cli_package_exposes_python_module_version() -> None:
    package = package_identity_report()
    source = package_source_label(package)
    source_note = f" ({source})" if source else ""
    result = subprocess.run(
        [sys.executable, "-m", "loopora", "--version"],
        capture_output=True,
        check=False,
        text=True,
        timeout=MODULE_HELP_TIMEOUT_SECONDS,
    )

    assert result.returncode == CLI_SUCCESS
    assert result.stdout.strip() == f"loopora {distribution('loopora').version}{source_note}"
    assert str(package.get("python_executable") or "") not in result.stdout


def test_cli_package_exposes_machine_readable_version_identity() -> None:
    package = package_identity_report()
    result = subprocess.run(
        [sys.executable, "-m", "loopora", "version", "--json"],
        capture_output=True,
        check=False,
        text=True,
        timeout=MODULE_HELP_TIMEOUT_SECONDS,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == CLI_SUCCESS
    assert next(iter(payload)) == "version_identity_summary"
    assert payload["schema_version"] == 1
    assert payload["redacted"] is True
    assert payload["version"] == distribution("loopora").version
    assert payload["source_revision"] == package["source_revision"]
    assert payload["source_tree_status"] == package["source_tree_status"]
    assert payload["version_identity_summary"] == {
        "schema_version": payload["schema_version"],
        "redacted": payload["redacted"],
        "name": payload["name"],
        "version": payload["version"],
        "source_revision": payload["source_revision"],
        "source_tree_status": payload["source_tree_status"],
        "source_label": payload["source_label"],
    }
    assert str(package.get("python_executable") or "") not in result.stdout
    assert "python_executable" not in result.stdout


def _assert_contains_all(text: str, terms: tuple[str, ...]) -> None:
    for term in terms:
        assert term in text


def _assert_compact_fit_first_use(plain) -> None:
    assert plain.exit_code == 0, plain.stdout
    _assert_contains_all(
        plain.stdout,
        (
            "Loopora fit",
            "Fit review: not started.",
            "Next: choose the target project, then describe the task:",
            'loopora fit --workdir "$PWD"',
            "will not install, create, or run anything during this review",
            "Rerun this command with --details",
        ),
    )
    assert (len(plain.stdout.splitlines()) <= 6, not any(fragment in plain.stdout for fragment in ("loopora init", "/loopora-run", "Completion command:"))) == (
        True,
        True,
    )


def test_cli_serve_prints_local_open_summary_without_starting_browser(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    calls: dict[str, object] = {}

    def fake_build_app(**kwargs):
        calls["build_app"] = kwargs
        return object()

    def fake_uvicorn_run(app, **kwargs) -> None:
        calls["uvicorn_app"] = app
        calls["uvicorn"] = kwargs

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fake_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fake_uvicorn_run)

    result = runner.invoke(cli.app, ["serve", "--host", "127.0.0.1", "--port", "9753", "--workdir", str(tmp_path)])

    assert result.exit_code == 0, result_error_text(result)
    _assert_contains_all(
        result.stdout,
        (
            "Loopora Web: http://127.0.0.1:9753",
            "home: http://127.0.0.1:9753",
            "fit guide: http://127.0.0.1:9753/fit-guide",
            "create: http://127.0.0.1:9753/loops/new",
            "support: http://127.0.0.1:9753/support",
            "auth: disabled (loopback local default)",
            "paths: local file dialogs enabled",
            f"workdir: {tmp_path}",
            "next: start from Fit Guide, then choose a Web path",
            "Fit Guide: decide whether Loopora fits before setup or creation",
            "Web conversation: browser-first planning",
            "Same-Agent setup: handoff back to Codex, Claude Code, or OpenCode",
            "Import/manual expert: preview an existing plan file or exact contract",
            "Existing work: inspect evidence, verdict state, residual risk, and next action",
        ),
    )
    assert "Agent Runner:" not in result.stdout
    assert calls["build_app"] == {"bind_host": "127.0.0.1", "bind_port": 9753, "auth_token": None, "startup_workdir": str(tmp_path)}
    assert calls["uvicorn"] == {"host": "127.0.0.1", "port": 9753, "log_level": "info", "access_log": False}


def test_cli_serve_refuses_occupied_port_before_printing_openable_url(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/.venv/bin/loopora"])
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    port = int(occupied.getsockname()[1])

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building the app when the port is occupied")

    def fail_uvicorn_run(_app, **_kwargs) -> None:
        raise AssertionError("serve should fail before starting uvicorn when the port is occupied")

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fail_uvicorn_run)
    try:
        result = runner.invoke(cli.app, ["serve", "--host", "127.0.0.1", "--port", str(port)])
    finally:
        occupied.close()
    assert result.exit_code == 1
    error_text = result_error_text(result)
    assert f"cannot start Loopora Web on http://127.0.0.1:{port}: port {port} is already in use" in error_text
    assert "Try `" in error_text
    assert f"{agent_adapter_command_prefix.current_project_file_loopora_cli_entry()} serve --open --host 127.0.0.1 --port" in error_text
    assert "Stop the existing service or choose another port." in error_text
    assert "Loopora Web:" not in result.stdout


def test_web_port_suggestion_wraps_from_upper_bound(monkeypatch) -> None:
    probed_ports: list[int] = []

    def fake_probe(_host: str, port: int) -> None:
        probed_ports.append(port)
        if port < 8744:
            raise OSError("occupied")

    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", fake_probe)
    assert web_bind_preflight.next_available_web_port(host="127.0.0.1", port=65535) == 8744
    assert probed_ports == [8742, 8743, 8744]


def test_cli_serve_remote_summary_redacts_auth_token_and_preserves_path_warning(monkeypatch) -> None:
    runner = CliRunner()
    secret_token = "secret-token-123"
    help_result = runner.invoke(cli.app, ["serve", "--help"])

    def fake_build_app(**_kwargs):
        return object()

    def fake_uvicorn_run(_app, **_kwargs) -> None:
        return None

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fake_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fake_uvicorn_run)
    result = runner.invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9754", "--auth-token", secret_token],
    )

    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    _assert_contains_all(
        normalized_help,
        (
            'serve --open --workdir "$PWD"',
            "127.0.0.1 --port 8742",
            "Fit Guide and Web choices entry",
            "start from Fit Guide",
            "browser-first planning path",
            "same-Agent setup",
            "import/manual expert",
            "existing-work views",
            "same-Agent path",
            'doctor --workdir "$PWD"',
            "custom Web host/port",
            "LOOPORA_AUTH_TOKEN",
            "unsafe opt-in",
        ),
    )
    assert result.exit_code == 0, result_error_text(result)
    assert "Agent Runner" not in normalized_help
    assert 'doctor --workdir "$PWD"` first' not in normalized_help
    assert "Loopora Web:" in result.stdout
    assert all(
        fragment in result.stdout
        for fragment in (
            "- open on this machine: http://127.0.0.1:9754",
            "- fit guide on this machine: http://127.0.0.1:9754/fit-guide",
            "- create on this machine: http://127.0.0.1:9754/loops/new",
            "- open from another machine: http://<server-host>:9754",
            "- fit guide from another machine: http://<server-host>:9754/fit-guide",
            "- create from another machine: http://<server-host>:9754/loops/new",
        )
    )
    assert "- bind: http://0.0.0.0:9754" in result.stdout
    assert "auth: enabled" in result.stdout
    assert "open the token form" in result.stdout
    assert "Authorization: Bearer" in result.stdout
    assert "?token=<your-token>" not in result.stdout
    assert "server-side absolute paths" in result.stdout
    assert "native file dialogs disabled" in result.stdout
    assert secret_token not in result.stdout


def test_cli_serve_refuses_non_loopback_without_auth_or_explicit_unsafe_opt_in(monkeypatch) -> None:
    runner = CliRunner()

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building the app")

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    result = runner.invoke(cli.app, ["serve", "--host", "0.0.0.0", "--port", "9755"])
    assert result.exit_code == 1
    assert all(fragment in result_error_text(result) for fragment in ("refusing to bind a non-loopback host without protection", "--auth-token '<token>'"))
    assert "Loopora Web:" not in result.stdout


def test_cli_serve_treats_blank_remote_auth_token_as_unprotected(monkeypatch) -> None:
    runner = CliRunner()

    def fail_build_app(**_kwargs):
        raise AssertionError("blank token must fail before building the app")

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    result = runner.invoke(cli.app, ["serve", "--host", "0.0.0.0", "--port", "9756", "--auth-token", "   "])
    assert result.exit_code == 1
    assert all(fragment in result_error_text(result) for fragment in ("refusing to bind a non-loopback host without protection", "--auth-token '<token>'"))
    assert "Loopora Web:" not in result.stdout


def test_cli_serve_passes_explicit_unsafe_remote_opt_in_to_web_boundary(monkeypatch) -> None:
    runner = CliRunner()
    calls: dict[str, object] = {}

    def fake_build_app(**kwargs):
        calls["build_app"] = kwargs
        return object()

    def fake_uvicorn_run(app, **kwargs) -> None:
        calls["uvicorn_app"] = app
        calls["uvicorn"] = kwargs

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fake_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fake_uvicorn_run)

    result = runner.invoke(cli.app, ["serve", "--host", "0.0.0.0", "--port", "9757", "--allow-unsafe-open"])

    assert result.exit_code == 0, result_error_text(result)
    assert calls["build_app"] == {
        "bind_host": "0.0.0.0",
        "bind_port": 9757,
        "auth_token": None,
        "allow_unsafe_open": True,
    }
    assert "auth: disabled by explicit --allow-unsafe-open" in result.stdout


def test_cli_fit_guidance_keeps_task_fit_boundary_actionable(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    (
        monkeypatch.setattr("loopora.fit_guidance.web_bind_preflight.probe_web_bind", lambda *_args: (_ for _ in ()).throw(OSError(errno.EADDRINUSE, "busy"))),
        monkeypatch.setattr("loopora.fit_guidance.web_bind_preflight.next_available_web_port", lambda **_kwargs: 9876),
        monkeypatch.setattr("loopora.fit_guidance_web_route.matching_configured_web_service", lambda *_args: False),
    )
    plain, details, json_result = (
        runner.invoke(cli.app, ["fit"]),
        runner.invoke(cli.app, ["fit", "--details"]),
        runner.invoke(cli.app, ["fit", "--json"]),
    )
    _assert_compact_fit_first_use(plain)
    assert details.exit_code == 0, details.stdout
    _assert_contains_all(
        details.stdout,
        (
            "Loopora fit guide",
            "Decision guide: not an automatic classifier",
            "Use Loopora when:",
            "multi-round Agent work",
            "Prefer direct Agent, /goal, or hard checks when:",
            "Answer before setup:",
            "Route choices stay hidden until the fit review is complete.",
        ),
    )
    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert next(iter(payload)) == "fit_guidance_summary"
    assert payload["schema_version"] == 2
    assert payload["language"] == "en"
    assert payload["fit_guidance_summary"]["language"] == "en"
    assert payload["fit_guidance_summary"]["recommended_path"] == "use_loopora_when_later_rounds_need_evidence_governance"
    assert payload["fit_guidance_summary"]["not_a_classifier"] is True
    assert (
        payload["target_project_required"],
        payload["route_commands_are_placeholders"],
        payload["setup_commands_ready"],
        payload["fit_review_recommended_before_setup"],
        payload["setup_command_readiness_scope"],
        payload["setup_command_blockers"],
        payload["route_preview_executable"],
        payload["route_preview_blockers"],
        payload["command_fields_are_local_only"],
        payload["command_fields_public_pasteable"],
        payload["fit_guidance_summary"]["direct_path_fallback_available"],
        payload["fit_guidance_summary"]["target_project_required"],
        payload["fit_guidance_summary"]["route_commands_are_placeholders"],
        payload["fit_guidance_summary"]["setup_commands_ready"],
        payload["fit_guidance_summary"]["fit_review_recommended_before_setup"],
        payload["fit_guidance_summary"]["setup_command_readiness_scope"],
        payload["fit_guidance_summary"]["setup_command_blockers"],
        payload["fit_guidance_summary"]["route_preview_executable"],
        payload["fit_guidance_summary"]["route_preview_blockers"],
        payload["fit_guidance_summary"]["command_fields_are_local_only"],
        payload["fit_guidance_summary"]["command_fields_public_pasteable"],
    ) == (
        True,
        True,
        False,
        True,
        "target_project_gate_fit_review_not_recorded",
        ["target_project_required"],
        False,
        ["target_project_required"],
        True,
        False,
        True,
        True,
        True,
        False,
        True,
        "target_project_gate_fit_review_not_recorded",
        ["target_project_required"],
        False,
        ["target_project_required"],
        True,
        False,
    )
    assert any("slow final feedback" in item for item in payload["strong_fit_signals"])
    assert any("one Agent pass" in item for item in payload["prefer_direct_agent_or_checks"])
    assert ([item["kind"] for item in payload["direct_path_next_actions"]], payload["fit_guidance_summary"]["direct_path_next_action_kinds"]) == (
        ["record_direct_decision", "use_direct_agent_or_hard_checks"],
        ["record_direct_decision", "use_direct_agent_or_hard_checks"],
    )
    assert (
        payload["direct_path_next_actions"][0]["command_ready"],
        payload["direct_path_next_actions"][0]["command_blockers"],
        "--direct-path '<what direct Agent, /goal, hard checks, or project process is enough>'" in payload["direct_path_next_actions"][0]["command_template"],
        "--task " not in payload["direct_path_next_actions"][0]["command_template"],
        "do not install same-Agent project entries" in payload["direct_path_next_actions"][1]["note"],
    ) == (False, ["direct_decision_input_required"], True, True, True)
    assert (
        [item["kind"] for item in payload["next_actions"]],
        payload["next_actions"][0]["command"],
        payload["next_actions"][0]["command_ready"],
        payload["next_actions"][0]["command_blockers"],
        payload["next_actions"][0]["local_only"],
        payload["next_actions"][1]["command"],
        payload["fit_guidance_summary"]["next_action_kinds"],
        "<project-dir>" not in json.dumps(payload["next_actions"]),
    ) == (["choose_workdir", "support"], f'{agent_adapter_command_prefix.current_copyable_loopora_cli_entry()} fit --workdir "$PWD"', True, [], True, f"{agent_adapter_command_prefix.current_copyable_loopora_cli_entry()} support", ["choose_workdir", "support"], True)
    assert (
        [item["kind"] for item in payload["route_actions_after_strong_fit"]],
        payload["fit_guidance_summary"]["route_action_kinds"],
        [item["command_ready"] for item in payload["route_actions_after_strong_fit"]],
        payload["route_actions_after_strong_fit"][1]["adapter_choices"][0]["local_only"],
        payload["route_actions_after_strong_fit"][3]["command_blockers"],
        payload["route_actions_after_strong_fit"][4]["command_blockers"],
    ) == (
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review", "support"],
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review", "support"],
        [False, False, False, False, False, False],
        True,
        ["target_project_required", "same_agent_entry_required", "first_task_message_not_ready"],
        ["target_project_required", "ready_review_required"],
    )
    assert [item["id"] for item in payload["task_review_questions"]] == ["strong_fit_signal", "direct_path_escape", "evidence_needed", "closure_blocker"]
    assert (
        payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:"),
        payload["first_task_message_example_state"]["copy_allowed"],
        payload["first_task_message_example_state"]["kind"],
    ) == (True, False, "generic_orientation_example")
    assert (
        payload["primary_first_task_message"],
        payload["primary_first_task_message_source"],
        payload["primary_first_task_message_status"],
        payload["primary_first_task_message_copy_allowed"],
        payload["fit_guidance_summary"]["primary_first_task_message_state"]["source"],
    ) == ("", "not_available_until_review", "example_only_no_task_review", False, "not_available_until_review")
    ready_plain, ready_json, partial_json, direct_plain, direct_json, direct_input_plain = (
        runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--details"]),
        runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--json"]),
        runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--task", "Migrate billing callbacks", "--json"]),
        runner.invoke(
            cli.app,
            [
                "fit",
                "--workdir",
                str(tmp_path),
                "--prefer-direct",
                "--task",
                "Migrate billing callbacks",
                "--direct-path",
                "One focused check is enough",
                "--details",
            ],
        ),
        runner.invoke(
            cli.app,
            [
                "fit",
                "--workdir",
                str(tmp_path),
                "--prefer-direct",
                "--task",
                "Migrate billing callbacks",
                "--direct-path",
                "One focused check is enough",
                "--json",
            ],
        ),
        runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--prefer-direct", "--details"]),
    )
    missing = tmp_path / "missing-target"
    missing_compact, missing_plain, missing_json = (
        runner.invoke(cli.app, ["fit", "--workdir", str(missing), *complete_fit_review_cli_args()]),
        runner.invoke(cli.app, ["fit", "--workdir", str(missing), "--details"]),
        runner.invoke(cli.app, ["fit", "--workdir", str(missing), "--json"]),
    )
    file_target = tmp_path / "not-a-directory"
    file_target.write_text("not a directory", encoding="utf-8")
    blocked_plain = runner.invoke(cli.app, ["fit", "--workdir", str(file_target), "--details"])
    blocked_json = runner.invoke(cli.app, ["fit", "--workdir", str(file_target), "--json"])
    assert all(
        result.exit_code == 0
        for result in (
            ready_plain,
            ready_json,
            partial_json,
            missing_compact,
            missing_plain,
            missing_json,
            blocked_plain,
            blocked_json,
            direct_plain,
            direct_json,
            direct_input_plain,
        )
    )
    ready_payload = json.loads(ready_json.stdout)
    assert (
        "Target project: not ready for Loopora routes." in missing_compact.stdout,
        f"mkdir -p {missing}" in missing_compact.stdout,
        "loopora init" not in missing_compact.stdout,
    ) == (True, True, True)
    assert_fit_unreviewed_plain_hides_routes(ready_plain.stdout)
    assert (
        ready_payload["workdir_state"]["status"],
        ready_payload["target_project_required"],
        ready_payload["route_commands_are_placeholders"],
        ready_payload["setup_commands_ready"],
        ready_payload["fit_review_recommended_before_setup"],
        ready_payload["setup_command_readiness_scope"],
        ready_payload["setup_command_blockers"],
        ready_payload["route_preview_executable"],
        ready_payload["route_preview_blockers"],
        ready_payload["setup_gate_ready"],
        ready_payload["setup_gate_blockers"],
        ready_payload["fit_guidance_summary"]["setup_gate_ready"],
        ready_payload["fit_guidance_summary"]["setup_gate_blockers"],
    ) == (
        "ready",
        False,
        False,
        True,
        True,
        "target_project_gate_fit_review_not_recorded",
        [],
        True,
        [],
        False,
        ["fit_review_required"],
        False,
        ["fit_review_required"],
    )
    route_actions_text = json.dumps(ready_payload["next_actions"])
    assert (
        ready_payload["workdir"] in route_actions_text,
        "<project-dir>" not in route_actions_text,
        [item["kind"] for item in ready_payload["next_actions"]],
        "command" in ready_payload["next_actions"][0],
        ready_payload["next_actions"][0]["command_ready"],
        ready_payload["next_actions"][0]["command_blockers"],
        "--task '<task goal>'" in ready_payload["next_actions"][0]["command_template"],
        [item["command_ready"] for item in ready_payload["route_actions_after_strong_fit"]],
        ready_payload["route_actions_after_strong_fit"][0]["command_blockers"],
        ready_payload["route_action_ready_kinds"],
        ready_payload["fit_guidance_summary"]["route_action_blocked_kinds"],
        ready_payload["fit_guidance_summary"]["web_route_command_ready"],
        ready_payload["fit_guidance_summary"]["web_route_command_blockers"],
        ready_payload["fit_guidance_summary"]["web_route_preflight_status"],
        ready_payload["route_actions_after_strong_fit"][2]["command"].endswith(" --web-host 127.0.0.1 --web-port 9876"),
        ready_payload["route_actions_after_strong_fit"][5]["command"].endswith(" --web-host 127.0.0.1 --web-port 9876"),
    ) == (
        True,
        True,
        ["complete_review_inputs"],
        False,
        False,
        ["review_inputs_required"],
        True,
        [False, False, False, False, False, True],
        ["fit_review_required"],
        ["support"],
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review"],
        False,
        ["fit_review_required"],
        "default_port_in_use_with_suggestion",
        True,
        True,
    )
    partial_payload = json.loads(partial_json.stdout)
    direct_payload = json.loads(direct_json.stdout)
    assert (
        partial_payload["setup_command_blockers"],
        partial_payload["fit_review_recommended_before_setup"],
        partial_payload["setup_command_readiness_scope"],
        partial_payload["task_fit_review"]["review_completion_command"].split("--workdir ", 1)[1].split(" --task", 1)[0],
        partial_payload["setup_gate_ready"],
        partial_payload["setup_gate_blockers"],
        partial_payload["fit_guidance_summary"]["setup_gate_blockers"],
        [action["kind"] for action in partial_payload["next_actions"]],
        partial_payload["next_actions"][1]["command"].endswith(" --web-host 127.0.0.1 --web-port 9876"),
            "Usage/setup help:"
            in runner.invoke(cli.app, ["fit", "--workdir", str(tmp_path), "--task", "Migrate billing callbacks", "--details"]).stdout,
        bool(
            partial_start_actions := json.loads(
                runner.invoke(cli.app, ["start", "--workdir", str(tmp_path), "--task", "Migrate billing callbacks", "--json"]).stdout
            )["next_actions"]
        ),
        [action["kind"] for action in partial_start_actions],
        partial_start_actions[1]["command"].endswith(" --web-host 127.0.0.1 --web-port 9876"),
    ) == (
        ["review_inputs_required"],
        False,
        "target_project_and_fit_review",
        partial_payload["workdir"],
        False,
        ["review_inputs_required"],
        ["review_inputs_required"],
        ["complete_review_inputs", "support", "continue_if_strong_fit"],
        True,
        True,
        True,
        ["complete_review_inputs", "support", "continue_if_strong_fit"],
        True,
    )
    missing_payload = json.loads(missing_json.stdout)
    assert (
        missing_payload["workdir_state"]["status"],
        missing_payload["target_project_required"],
        missing_payload["route_commands_are_placeholders"],
        missing_payload["fit_review_recommended_before_setup"],
        missing_payload["setup_command_readiness_scope"],
        missing_payload["setup_command_blockers"],
        missing_payload["route_preview_executable"],
        missing_payload["route_preview_blockers"],
    ) == ("missing", False, False, True, "target_project_gate_fit_review_not_recorded", ["target_project_unready"], False, ["target_project_unready"])
    assert (
        [action["kind"] for action in missing_payload["next_actions"]],
        missing_payload["next_actions"][2]["command_ready"],
        missing_payload["route_actions_after_strong_fit"][0]["kind"],
    ) == (["create_workdir", "confirm_readiness", "support"], True, "open_web_creation_choices")
    assert all(
        term in missing_plain.stdout
        for term in (
            "Next before setup:",
            "Create target directory:",
            "Route choices stay hidden until the fit review is complete.",
        )
    )
    blocked_payload = json.loads(blocked_json.stdout)
    assert (
        blocked_payload["workdir_state"]["status"],
        blocked_payload["target_project_required"],
        blocked_payload["route_commands_are_placeholders"],
        blocked_payload["fit_review_recommended_before_setup"],
        blocked_payload["setup_command_readiness_scope"],
        blocked_payload["setup_command_blockers"],
        blocked_payload["route_preview_executable"],
        blocked_payload["route_preview_blockers"],
    ) == ("not_directory", True, True, True, "target_project_gate_fit_review_not_recorded", ["target_project_required"], False, ["target_project_required"])
    assert (
        [action["kind"] for action in blocked_payload["next_actions"]],
        blocked_payload["next_actions"][1]["command_ready"],
        blocked_payload["next_actions"][1]["command_blockers"],
    ) == (["choose_workdir", "support"], True, [])
    assert (
        "Target project path exists but is not a directory" in blocked_plain.stdout,
        "serve --workdir '<project-dir>'" not in blocked_plain.stdout,
        "loopora support --workdir" in blocked_plain.stdout,
    ) == (True, True, True)
    assert (
        direct_payload["setup_command_blockers"],
        direct_payload["setup_gate_ready"],
        direct_payload["setup_gate_blockers"],
        direct_payload["task_review_status"],
        direct_payload["setup_allowed"],
        direct_payload["fit_guidance_summary"]["task_review_status"],
        direct_payload["fit_guidance_summary"]["setup_allowed"],
        direct_payload["route_actions_after_strong_fit"],
        [action["kind"] for action in direct_payload["next_actions"]],
        direct_payload["direct_path_next_action_kinds"],
        direct_payload["direct_path_next_action_blocked_kinds"],
        direct_payload["next_actions"][1]["command"].endswith(" --web-host 127.0.0.1 --web-port 9876"),
        f"Usage/setup help: {agent_adapter_command_prefix.current_copyable_loopora_cli_entry()} support --workdir" in direct_plain.stdout,
        "loopora init" not in direct_plain.stdout,
        "Choose the route:" not in direct_plain.stdout,
        "Next before recording the direct-path decision:" in direct_input_plain.stdout,
        "Next before setup:" not in direct_input_plain.stdout,
    ) == (
        ["prefer_direct_path"],
        False,
        ["prefer_direct_path"],
        "direct_path_selected",
        False,
        "direct_path_selected",
        False,
        [],
        ["use_direct_agent_or_hard_checks", "support"],
        ["use_direct_agent_or_hard_checks"],
        [],
        True,
        True,
        True,
        True,
        True,
        True,
    )


def test_cli_start_help_uses_start_guide_option_language() -> None:
    result = CliRunner().invoke(cli.app, ["start", "--help"])
    normalized = re.sub(r"\s+", " ", result.stdout)
    assert result.exit_code == 0, result_error_text(result)
    assert all(
        fragment in normalized
        for fragment in (
            "Target project directory",
            "readiness gating",
            "Start guide output language",
            "en or zh",
            "is read-only",
            "does not install, start Web, create a Loop, or classify the task",
            "the default output shows one recommended next action",
            "--details",
            "full fit record",
            "every Web/same-Agent/import route",
            "run remains blocked until READY review",
        )
    )
    assert all(fragment not in normalized for fragment in ("support-guide", "public doctor command"))


def test_cli_fit_json_reports_invalid_language_as_structured_error() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.app, ["fit", "--language", "fr", "--json"])
    plain = runner.invoke(cli.app, ["fit", "--language", "fr"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["error"].startswith("invalid --language: expected one of: en, zh")
    for term in ("en-US", "en-GB", "zh-CN", "zh-Hans", "中文"):
        assert term in payload["error"]
    assert result.stderr == ""
    assert plain.exit_code == 2
    for term in ("invalid --language", "zh-CN", "en-US"):
        assert term in plain.stderr


def test_cli_fit_language_aliases_normalize_to_canonical_language_and_commands() -> None:
    runner = CliRunner()

    zh_result = runner.invoke(cli.app, ["fit", "--language", "zh-CN", "--task", "迁移账单回调", "--json"])
    en_result = runner.invoke(cli.app, ["fit", "--language", "en-US", "--task", "Migrate billing callbacks", "--json"])
    help_result = runner.invoke(cli.app, ["fit", "--help"])

    assert zh_result.exit_code == 0, zh_result.stdout
    zh_payload = json.loads(zh_result.stdout)
    assert zh_payload["language"] == "zh"
    assert zh_payload["task_fit_review"]["review_completion_command"].startswith(f"{agent_adapter_command_prefix.current_copyable_loopora_cli_entry()} fit --language zh --task")
    assert "--language zh-CN" not in zh_payload["task_fit_review"]["review_completion_command"]
    assert all(choice["command"].endswith("--language zh") for choice in zh_payload["route_actions_after_strong_fit"][1]["adapter_choices"])
    assert (zh_payload["route_actions_after_strong_fit"][1]["current_agent_host"]["state"], "command" in zh_payload["route_actions_after_strong_fit"][1]) == ("unavailable", False)
    assert zh_payload["route_actions_after_strong_fit"][2]["command"].endswith("--language zh")

    assert en_result.exit_code == 0, en_result.stdout
    en_payload = json.loads(en_result.stdout)
    assert en_payload["language"] == "en"
    assert "--language" not in en_payload["task_fit_review"]["review_completion_command"]

    assert help_result.exit_code == 0, help_result.stdout
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    for term in ("common", "aliases", "en-US", "zh-CN", "normalized"):
        assert term in normalized_help
    for term in (
        "human pre-setup decision",
        "not an automatic classifier",
        "default output shows the current decision and next action",
        "--details",
        "every judgment field",
        "direct Agent work",
        "Fit Guide/Web choices",
        "outside an Agent session",
        "Web conversation",
        "Plan File import",
        "manual expert paths",
        "current host entry",
        "--workdir",
        "Target project directory",
        "Setup remains blocked until a strong-fit review is complete",
        "run only after READY review",
    ):
        assert term in normalized_help
