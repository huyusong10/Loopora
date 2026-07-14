from __future__ import annotations

import json
import re
import shlex
import socket
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli
from loopora.branding import APP_AUTH_ENV, APP_HOME_ENV

from cli_diagnose_redaction_test_support import (
    assert_public_auth_blocker_payload as _assert_public_auth_blocker_payload,
    assert_public_network_web_startable_payload as _assert_public_network_web_startable_payload,
    assert_public_port_blocker_payload as _assert_public_port_blocker_payload,
    public_doctor_payload as _public_doctor_payload,
)
from cli_first_use_docs_test_support import (
    _entry,
    assert_before_install_doctor_payload as _assert_before_install_doctor_payload,
    assert_command_uses_home_and_workdir as _assert_command_uses_home_and_workdir,
    assert_init_next_order as _assert_init_next_order,
    assert_public_action_summaries as _assert_public_action_summaries,
    command_tokens as _command_tokens,
    free_local_port as _free_local_port,
    assert_before_install_doctor_plain_output,
    assert_cli_agent_entry_help,
    assert_cli_bundle_import_help,
    assert_init_help_scannable_first_use_path,
    assert_ready_doctor_plain_output,
    assert_root_help_scannable_first_use_path,
    result_error_text,
)


def test_cli_help_keeps_first_use_language_on_plan_files(monkeypatch) -> None:
    runner = CliRunner()
    root_no_args = runner.invoke(cli.app, [])
    root_help, serve_help = runner.invoke(cli.app, ["--help"]), runner.invoke(cli.app, ["serve", "--help"])
    init_no_args = runner.invoke(cli.app, ["init"])
    uninstall_no_args = runner.invoke(cli.app, ["uninstall"])
    normalized_root_help = re.sub(r"\s+", " ", root_help.stdout)
    normalized_init_help = re.sub(r"\s+", " ", init_no_args.stdout)
    normalized_uninstall_help = re.sub(r"\s+", " ", uninstall_no_args.stdout)
    assert root_no_args.exit_code == 0, result_error_text(root_no_args)
    assert_root_help_scannable_first_use_path(root_no_args.stdout)
    assert "Missing command" not in result_error_text(root_no_args)
    assert root_no_args.stdout == root_help.stdout
    assert (root_help.exit_code, serve_help.exit_code) == (0, 0), result_error_text(root_help) + result_error_text(serve_help)
    assert all(
        term in normalized_root_help
        for term in (
            "Show when Loopora fits a task before setup or planning.",
            "Import, export, and manage Loop plan files",
            "Set up same-Agent project entries",
            "/loopora-plan",
            "/loopora-run",
            "Report local first-use readiness",
            "Remove Loopora-managed Coding Agent project entries",
            "Contributor checks:",
            "`loopora dev check`",
            "Add `--details` to start or fit",
        )
    )
    assert all(
        term not in root_help.stdout
        for term in (
            "Expert: create and run a Loop from an existing spec file.",
            "Expert: create and inspect reusable run flows",
            "Expert: create and inspect reusable role definitions",
            "Expert: work with Markdown Loop contracts",
            "Expert: inspect and validate Strategy Source prompt assets",
            "Developer: run local checks and reset incompatible development state",
            "Internal runtime used by /loopora-plan and /loopora-run project entries",
        )
    )
    assert "run `loopora start` first" in " ".join(runner.invoke(cli.app, ["agent", "--help"]).stdout.split())
    assert "Expert direct-run path" in " ".join(runner.invoke(cli.app, ["run", "--help"]).stdout.split())
    assert all(term in normalized_root_help for term in ("loopora fit", "If fit is uncertain", "Run only after READY review"))
    assert (
        all(fragment not in root_help.stdout for fragment in ("Import and manage YAML bundles", "Coding Agent adapters")),
        "your current Codex, Claude Code, or OpenCode host" in re.sub(r"\s+", " ", serve_help.stdout),
    ) == (True, True)
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/src/loopora/__main__.py"])
    source_help, source_entry = (
        cli._help_with_current_loopora_entry(
            cli.ROOT_FIRST_USE_HELP + " loopora init <agent> --workdir loopora serve --open --workdir loopora run loopora diagnose doctor --workdir"
        ),
        agent_adapter_command_prefix.current_project_file_loopora_cli_entry(),
    )
    for fragment in ("start", "fit", "init <agent> --workdir", "doctor --workdir", "serve --open --workdir", "run", "diagnose doctor --workdir"):
        assert f"{source_entry} {fragment}" in source_help
    assert f'{source_entry} start --workdir "$PWD"' in source_help
    assert "--language zh" in source_help
    assert init_no_args.exit_code == 0, result_error_text(init_no_args)
    assert "Usage:" in init_no_args.stdout
    assert "codex" in init_no_args.stdout
    assert "claude" in init_no_args.stdout
    assert "opencode" in init_no_args.stdout
    assert "If you are not sure this task needs a Loop" in init_no_args.stdout
    assert_init_help_scannable_first_use_path(init_no_args.stdout)
    assert all(
        fragment in normalized_init_help
        for fragment in (
            "After readiness passes",
            "choose one path",
            "Fit Guide/Web choices",
            "Fit Guide first, then creation choices",
            "Web conversation outside an Agent session",
            "Plan File import",
            "Plan-file/expert path",
            "Existing work path",
            "review evidence, gaps, and verdicts",
        )
    )
    _assert_init_next_order(normalized_init_help)
    assert "Missing command" not in result_error_text(init_no_args)
    assert uninstall_no_args.exit_code == 0, result_error_text(uninstall_no_args)
    assert all(fragment in normalized_uninstall_help for fragment in ("uninstall <agent>", 'doctor --workdir "$PWD"', "Reinstall later", "refresh or restart"))
    assert "Missing command" not in result_error_text(uninstall_no_args)

    assert_cli_agent_entry_help(runner)
    assert_cli_bundle_import_help(runner)


def test_cli_command_groups_show_help_without_missing_command_error() -> None:
    runner = CliRunner()
    command_groups = {
        ("init",): ("codex", "claude", "opencode"),
        ("uninstall",): ("codex", "claude", "opencode"),
        ("diagnose",): ("doctor", 'loopora doctor --workdir "$PWD"', "diagnostics-group alias", "event-redaction"),
        ("dev",): ("check", "reset"),
        ("bundles",): ("import", "export"),
        ("loops",): ("run",),
        ("prompts",): ("validate",),
        ("spec",): ("init",),
        ("roles",): ("create",),
        ("orchestrations",): ("create",),
        ("agent",): ("codex", 'doctor --workdir "$PWD"', "/loopora-plan", "agent <agent> check"),
        ("agent", "codex"): ("plan", "run", "next", "submit", "check", "loopora init codex", "agent codex check"),
    }

    for args, expected_terms in command_groups.items():
        result = runner.invoke(cli.app, list(args))
        assert result.exit_code == 0, result_error_text(result)
        assert "Usage:" in result.stdout
        assert "Missing command" not in result_error_text(result)
        for term in expected_terms:
            assert term in result.stdout

    unknown = runner.invoke(cli.app, ["dev", "unknown"])
    assert unknown.exit_code == 2
    assert "No such command" in result_error_text(unknown)


def test_cli_init_group_help_exposes_readiness_and_web_next_steps_without_choosing_adapter() -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["init"])
    normalized_output = re.sub(r"\s+", " ", result.stdout)

    assert result.exit_code == 0, result_error_text(result)
    assert "If you are not sure this task needs a Loop" in result.stdout
    _assert_init_next_order(normalized_output)
    assert "codex" in result.stdout
    assert "claude" in result.stdout
    assert "opencode" in result.stdout
    assert "Installing" not in result.stdout
    assert "Missing command" not in result_error_text(result)


def test_cli_diagnose_doctor_before_install_json_reports_actionable_first_use(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port()

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(web_port), "--json"])

    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    _assert_before_install_doctor_payload(payload, workdir=tmp_path, web_port=web_port)

    alias_result = runner.invoke(
        cli.app,
        ["diagnose", "doctor", "--workdir", str(tmp_path), "--web-port", str(web_port), "--json"],
    )
    alias_payload = json.loads(alias_result.stdout)

    assert alias_result.exit_code == 1, alias_result.stdout
    assert alias_payload["diagnose_doctor_summary"] == payload["diagnose_doctor_summary"]


def test_cli_doctor_source_checkout_requires_explicit_target_before_readiness() -> None:
    runner = CliRunner()
    plain = runner.invoke(cli.app, ["doctor"])
    payload_result = runner.invoke(cli.app, ["doctor", "--json"])
    public_result = runner.invoke(cli.app, ["doctor", "--public-json"])
    explicit_result = runner.invoke(cli.app, ["doctor", "--workdir", str(Path.cwd()), "--json"])
    payload, public_payload, explicit_payload = json.loads(payload_result.stdout), json.loads(public_result.stdout), json.loads(explicit_result.stdout)
    cwd = str(Path.cwd().resolve())

    assert plain.exit_code == payload_result.exit_code == public_result.exit_code == explicit_result.exit_code == 1
    assert (
        "Loopora doctor: target_required" in plain.stdout,
        'doctor --workdir "$PWD"' in plain.stdout,
        "loopora init codex --workdir" not in plain.stdout,
        "App state:" not in plain.stdout,
    ) == (True, True, True, True)
    assert (payload["status"], payload["target_project_required"], payload["next_action_kinds"]) == (
        "target_required",
        True,
        ["choose_workdir", "check_fit_first", "support"],
    )
    assert (
        public_payload["status"],
        public_payload["target_project_required"],
        "python_executable" not in public_result.stdout,
        cwd not in public_result.stdout,
    ) == ("target_required", True, True, True)
    assert (explicit_payload["status"] != "target_required", explicit_payload.get("target_project_required", False), explicit_payload["workdir"]) == (
        True,
        False,
        cwd,
    )


def test_cli_diagnose_doctor_before_install_human_output_requires_host_choice(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port()

    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(web_port)])

    assert_before_install_doctor_plain_output(plain)


def test_cli_diagnose_doctor_defers_app_web_commands_until_project_directory_is_usable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_home = tmp_path / "loopora-home"
    app_home.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("PRAGMA user_version = 1")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    missing_workdir = tmp_path / "missing project"
    file_workdir = tmp_path / "not-a-project"
    file_workdir.write_text("not a directory\n", encoding="utf-8")

    for workdir, status, action_kind in [
        (missing_workdir, "missing", "create_workdir"),
        (file_workdir, "not_directory", "choose_workdir"),
    ]:
        payload_result = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--json"])
        plain = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir)])
        payload = json.loads(payload_result.stdout)

        assert payload_result.exit_code == 1, payload_result.stdout
        assert payload["workdir_state"]["status"] == status
        assert payload["app_state"]["status"] == "development_reset_required"
        assert payload["app_state"]["commands"] == {}
        assert all(entry["commands"] == {} for entry in payload["agent_entries"])
        assert ([item["kind"] for item in payload["next_action_items"]], payload["first_task_handoff_executable"], payload["first_task_handoff_blockers"]) == (
            [action_kind, "confirm_readiness", "support"],
            False,
            ["target_project_unready", "same_agent_entry_required"],
        )
        assert plain.exit_code == 1, plain.stdout
        assert all(
            term in plain.stdout
            for term in (
                f"project directory state: {status}",
                "/loopora-plan handoff is not ready yet",
                "usable target project",
                "same-Agent project entry",
                "Usage/setup help:",
            )
        )
        assert "readiness summary: blocked until target project directory and same-Agent project entry are ready." in plain.stdout
        assert "App state:" not in plain.stdout
        assert "web:" not in plain.stdout
        assert "loopora dev reset" not in plain.stdout
        assert "loopora serve" not in plain.stdout


def test_cli_diagnose_doctor_json_next_action_commands_are_shell_safe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    loopora_home, workdir = tmp_path / "home with spaces", tmp_path / "project with spaces"
    loopora_home.mkdir()
    workdir.mkdir()
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/src/loopora/__main__.py"])
    database = loopora_home / "app.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=1")

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(_free_local_port()), "--json"])

    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "create_recovery_archive",
        "preview_app_database_reset",
        "use_temporary_app_home",
        "confirm_readiness",
        "check_fit_first",
        "install_agent_entry",
        "run_loopora_plan",
        "support",
    ]
    assert payload["primary_next_action_kind"] == payload["diagnose_doctor_summary"]["primary_next_action_kind"] == "create_recovery_archive"
    entry_tokens = shlex.split(agent_adapter_command_prefix.current_project_file_loopora_cli_entry())
    assert _command_tokens(payload["next_action_items"][4]["command"]) == [
        f"LOOPORA_HOME={loopora_home!s}",
        *entry_tokens,
        "fit",
        "--workdir",
        str(workdir),
    ]
    items = payload["next_action_items"]
    assert [(item["kind"], item.get("command_ready"), item.get("command_blockers")) for item in items if item.get("command")] == [
        ("create_recovery_archive", True, []),
        ("preview_app_database_reset", True, []),
        ("use_temporary_app_home", True, []),
        ("confirm_readiness", True, []),
        ("check_fit_first", True, []),
        ("run_loopora_plan", False, ["same_agent_entry_required", "app_state_not_ready"]),
        ("support", True, []),
    ]
    install_choices = [choice["command"] for choice in items[5]["adapter_choices"]]
    assert all(choice["command_ready"] is True and choice["command_blockers"] == [] for choice in items[5]["adapter_choices"])
    archive_command, reset_command, temporary_command, confirm_command, support_command = [
        items[i]["command"] for i in (0, 1, 2, 3, 7)
    ]
    for command in (*install_choices, archive_command, reset_command, confirm_command, support_command):
        _assert_command_uses_home_and_workdir(command, loopora_home=loopora_home, workdir=workdir)
    assert "command" not in items[5]
    assert all(_command_tokens(command)[1 : 1 + len(entry_tokens) + 1] == [*entry_tokens, "init"] for command in install_choices)
    assert _command_tokens(archive_command)[1 : 1 + len(entry_tokens) + 2] == [*entry_tokens, "recovery", "create"]
    assert _command_tokens(reset_command)[1 : 1 + len(entry_tokens) + 3] == [*entry_tokens, "dev", "reset", "--scope"]
    _assert_command_uses_home_and_workdir(temporary_command, loopora_home="$(mktemp -d)", workdir=workdir)
    assert _command_tokens(temporary_command)[1 : 1 + len(entry_tokens) + 1] == [*entry_tokens, "serve"]
    assert _command_tokens(confirm_command)[1 : 1 + len(entry_tokens) + 1] == [*entry_tokens, "doctor"]
    assert all(
        any(command in step for step in payload["next_steps"])
        for command in (archive_command, reset_command, confirm_command)
    )
    assert "LOOPORA_HOME='home with spaces'" not in result.stdout


def test_cli_diagnose_doctor_public_json_omits_local_paths_and_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port()

    result = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-port", str(web_port), "--public-json"],
    )
    payload = json.loads(result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)

    assert result.exit_code == 1, result.stdout
    assert next(iter(payload)) == "diagnose_doctor_public_summary"
    assert payload["schema_version"] == 2
    assert payload["diagnose_doctor_public_summary"]["schema_version"] == 2
    assert payload["diagnose_doctor_public_summary"]["redacted"] is True
    assert payload["redacted"] is True
    assert payload["doctor_schema_version"] == 2
    assert payload["status"] == "not_ready"
    assert payload["ready"] is False
    assert payload["agent_entry_ready"] is False
    assert payload["strict_ready"] is False
    assert payload["diagnose_doctor_public_summary"]["agent_entry_ready"] is False
    assert payload["diagnose_doctor_public_summary"]["strict_ready"] is False
    assert payload["project_directory_status"] == "ready"
    assert payload["diagnose_doctor_public_summary"]["project_directory_status"] == "ready"
    assert payload["diagnose_doctor_public_summary"]["first_task_guidance_available"] is payload["first_task_guidance_available"] is True
    assert payload["first_task_handoff_policy"] == {
        "preferred_source": "completed_fit_review",
        "fallback_source": "generic_example",
    }
    assert (
        payload["diagnose_doctor_public_summary"]["first_task_handoff_policy"],
        payload["first_task_handoff_executable"],
        payload["diagnose_doctor_public_summary"]["first_task_handoff_executable"],
        payload["first_task_handoff_blockers"],
    ) == (payload["first_task_handoff_policy"], False, False, ["same_agent_entry_required"])
    assert payload["environment"]["python"] == payload["package"]["python"]
    assert payload["environment"]["python_implementation"]
    assert payload["environment"]["os"]
    assert payload["environment"]["machine"]
    assert payload["diagnose_doctor_public_summary"]["environment"] == payload["environment"]
    assert payload["app_state"]["status"] == "not_initialized"
    assert payload["web"]["loopback"] is True
    assert payload["web"]["recovery_action"] == "start_web_after_readiness"
    assert payload["web"]["alternate_port_available"] is False
    assert payload["diagnose_doctor_public_summary"]["web_start_available"] == payload["web"]["start_available"]
    assert payload["diagnose_doctor_public_summary"]["web_start_blocked_reason"] == payload["web"]["start_blocked_reason"]
    assert payload["diagnose_doctor_public_summary"]["web_recovery_action"] == payload["web"]["recovery_action"]
    assert (
        payload["next_actions"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    ) == (
        ["check_fit_first", "install_agent_entry", "confirm_readiness", "run_loopora_plan", "support"],
        ["check_fit_first", "install_agent_entry", "support"],
        {"confirm_readiness": "install_agent_entry"},
        ["run_loopora_plan"],
        {"run_loopora_plan": ["same_agent_entry_required"]},
    )
    assert (
        payload["diagnose_doctor_public_summary"]["next_actions"],
        payload["primary_next_action_kind"],
        payload["diagnose_doctor_public_summary"]["primary_next_action_kind"],
    ) == (payload["next_actions"], "check_fit_first", "check_fit_first")
    _assert_public_action_summaries(
        payload,
        expected_terms=(
            "static fit guide",
            "same-Agent project entry that matches the current host",
            "After installing the matching same-Agent project entry",
            "support guidance",
        ),
    )
    assert any(item["adapter"] == "codex" and item["next_action"] == "install_agent_entry" for item in payload["agent_entries"])
    assert str(tmp_path) not in encoded
    assert str(web_port) not in encoded
    assert "workdir" not in encoded
    assert "commands" not in encoded
    assert not any(fragment in encoded for fragment in ("loopora doctor", "loopora fit", "/loopora-plan"))
    assert '"first_task_message_example"' not in encoded
    assert "python_executable" not in encoded
    assert "db_path" not in encoded

    alias = runner.invoke(
        cli.app,
        ["diagnose", "doctor", "--workdir", str(tmp_path), "--web-port", str(web_port), "--public-json"],
    )
    assert alias.exit_code == 1, alias.stdout
    assert json.loads(alias.stdout)["diagnose_doctor_public_summary"] == payload["diagnose_doctor_public_summary"]


def test_cli_diagnose_doctor_public_summary_surfaces_redacted_web_start_blockers(tmp_path: Path) -> None:
    runner = CliRunner()
    secret = "secret-token-123"
    web_port = _free_local_port("0.0.0.0")

    payload, encoded = _public_doctor_payload(
        runner,
        tmp_path,
        web_host="0.0.0.0",
        web_port=web_port,
        env={APP_AUTH_ENV: secret},
    )
    _assert_public_network_web_startable_payload(payload, encoded, web_port=web_port, secret=secret)

    auth_payload, auth_encoded = _public_doctor_payload(
        runner,
        tmp_path,
        web_host="0.0.0.0",
        web_port=_free_local_port("0.0.0.0"),
    )
    _assert_public_auth_blocker_payload(auth_payload, auth_encoded)

    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    occupied_port = int(occupied.getsockname()[1])
    try:
        port_payload, port_encoded = _public_doctor_payload(runner, tmp_path, web_port=occupied_port)
    finally:
        occupied.close()
    _assert_public_port_blocker_payload(port_payload, port_encoded, occupied_port=occupied_port)


def test_cli_diagnose_doctor_ready_after_one_agent_entry_install(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port()
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, install.stdout

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(web_port), "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["ready"] is True
    assert payload["agent_entry_ready"] is True
    assert payload["strict_ready"] is True
    assert payload["app_state"]["status"] == "not_initialized"
    assert payload["app_state"]["web_ready"] is True
    assert payload["web"]["port"] == web_port
    assert payload["web"]["start_available"] is True
    assert payload["diagnose_doctor_summary"]["web_access_mode"] == "start_or_open"
    assert payload["ready_adapter_count"] == 1
    assert payload["attention_adapter_count"] == 0
    assert payload["diagnose_doctor_summary"]["first_task_guidance_available"] is True
    assert payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert payload["first_task_handoff_policy"]["fallback_source"] == "generic_example"

    codex = _entry(payload, "codex")
    assert codex["ready"] is True
    assert codex["check_status"] == "pass"
    assert codex["install_state"] == "installed"
    assert codex["next_action"] == "return_to_agent"
    assert "loopora init codex" in codex["commands"]["install_check"]
    assert "loopora agent codex check" in codex["commands"]["agent_check"]

    claude = _entry(payload, "claude")
    assert claude["ready"] is False
    assert claude["install_state"] == "not_installed"
    assert claude["next_action"] == "install_agent_entry"
    assert "loopora init claude" in claude["commands"]["install"]
    assert any("/loopora-plan" in step for step in payload["next_steps"])
    assert any("/loopora-run" in step for step in payload["next_steps"])
    action_kinds = [item["kind"] for item in payload["next_action_items"]]
    assert payload["next_actions"] == payload["next_action_items"]
    assert action_kinds == [
        "return_to_agent",
        "confirm_agent_visibility",
        "run_loopora_plan",
        "review_ready_loop_preview",
        "run_loopora_run",
        "support",
        "start_web",
    ]
    assert payload["diagnose_doctor_summary"]["next_action_kinds"] == action_kinds
    assert [(item["kind"], item.get("command_ready"), item.get("command_blockers")) for item in payload["next_action_items"] if item.get("command")] == [
        ("run_loopora_plan", True, []),
        ("run_loopora_run", False, ["ready_review_required"]),
        ("support", True, []),
        ("start_web", True, []),
    ]
    assert payload["next_action_items"][0]["adapter"] == "codex"
    assert payload["next_action_items"][1]["adapter"] == "codex"
    assert payload["next_action_items"][2]["command"] == "/loopora-plan"
    assert payload["next_action_items"][4]["command"] == "/loopora-run"

    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(web_port)])
    assert_ready_doctor_plain_output(plain, web_port=web_port)


def test_cli_diagnose_doctor_next_steps_use_structured_web_command(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    loopora_home = tmp_path / "home with spaces"
    workdir = tmp_path / "project"
    loopora_home.mkdir()
    workdir.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOOPORA_HOME", "home with spaces")
    web_port = _free_local_port()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir)])
    result = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--json"])

    assert install.exit_code == 0, install.stdout
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    web_command = payload["web"]["start_command"]
    _assert_command_uses_home_and_workdir(web_command, loopora_home=loopora_home, workdir=workdir)
    assert "LOOPORA_HOME='home with spaces'" not in web_command
    assert payload["next_action_items"][-1]["kind"] == "start_web"
    assert payload["next_action_items"][-1]["operation"] == "start_or_open"
    assert payload["next_action_items"][-1]["already_running"] is False
    assert payload["next_action_items"][-1]["command"] == web_command
    assert any(web_command in step for step in payload["next_steps"])


def test_cli_doctor_is_visible_as_first_use_root_command() -> None:
    runner = CliRunner()

    help_result = runner.invoke(cli.app, ["--help"])
    doctor_help = runner.invoke(cli.app, ["doctor", "--help"])
    grouped_help = runner.invoke(cli.app, ["diagnose", "doctor", "--help"])
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    doctor_help_surfaces = [
        re.sub(r"\s+", " ", doctor_help.stdout),
        re.sub(r"\s+", " ", grouped_help.stdout),
    ]

    assert help_result.exit_code == 0, help_result.stdout
    assert 'Readiness: `loopora doctor --workdir "$PWD"`' in normalized_help
    assert "Add `--details` to start or fit for every route and diagnostic" in normalized_help
    assert "<project-dir>" not in normalized_help
    assert "│ doctor" in help_result.stdout
    assert help_result.stdout.index("│ serve") < help_result.stdout.index("│ init") < help_result.stdout.index("│ doctor")
    assert doctor_help.exit_code == 0, doctor_help.stdout
    assert grouped_help.exit_code == 0, grouped_help.stdout
    for surface in doctor_help_surfaces:
        assert all(term in surface for term in ("Report local first-use readiness", "read-only readiness checkpoint"))
        assert all(
            term in surface
            for term in ('loopora init current --workdir "$PWD"', "explicit", "loopora init <agent>", "--web-host/--web-port")
        )
        assert all(term in surface for term in ("--json for automation", "--public-json for redacted public issue reports", "--strict"))


def test_cli_diagnose_doctor_suggests_free_web_port_when_configured_port_is_occupied(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.setattr("loopora.diagnose_doctor_web_state.matching_configured_web_service", lambda *_args: False)
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, result_error_text(install)

    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    port = int(occupied.getsockname()[1])

    try:
        result = runner.invoke(
            cli.app,
            ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(port), "--json"],
        )
        plain = runner.invoke(
            cli.app,
            ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(port)],
        )
        strict = runner.invoke(
            cli.app,
            ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(port), "--strict"],
        )
    finally:
        occupied.close()

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert (payload["status"], payload["ready"], payload["strict_ready"]) == ("ready_with_warnings", True, False)
    assert (payload["diagnose_doctor_summary"]["web_start_available"], payload["diagnose_doctor_summary"]["web_start_blocked_reason"]) == (False, "port_in_use")
    assert (
        payload["web"]["requested_port"],
        payload["web"]["requested_origin"],
        payload["web"]["start_available"],
        payload["web"]["start_blocked_reason"],
    ) == (port, f"http://127.0.0.1:{port}", False, "port_in_use")
    assert payload["web"]["suggested_port"] != port
    assert payload["web"]["port"] == payload["web"]["suggested_port"]
    assert payload["web"]["suggested_start_command"] == payload["web"]["start_command"]
    assert f"--port {payload['web']['suggested_port']}" in payload["web"]["start_command"]
    assert (payload["next_action_items"][-1]["kind"], payload["next_action_items"][-1]["command"], payload["next_action_items"][-1]["origin"]) == (
        "resolve_web_port",
        payload["web"]["suggested_start_command"],
        payload["web"]["suggested_origin"],
    )
    assert any("Choose a free Web port" in step for step in payload["next_steps"])

    assert plain.exit_code == 0, plain.stdout
    assert all(
        fragment in plain.stdout
        for fragment in (
            f"web: http://127.0.0.1:{port} (port in use; loopback local default)",
            "web start unavailable:",
            f"loopora serve --open --host 127.0.0.1 --port {port}",
            f"suggested Web: {payload['web']['suggested_origin']}",
            f"web start: {payload['web']['suggested_start_command']}",
        )
    )
    assert "Loopora doctor: ready_with_warnings" in plain.stdout
    assert "readiness summary: same-Agent project entry is ready; strict readiness is blocked by Web start." in plain.stdout

    assert (strict.exit_code, "strict readiness: no" in strict.stdout) == (1, True)

    monkeypatch.setattr("loopora.diagnose_doctor.next_available_web_port", lambda **_kwargs: None)
    occupied_again = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied_again.bind(("127.0.0.1", 0))
    occupied_again.listen(1)
    no_suggestion_port = int(occupied_again.getsockname()[1])
    try:
        no_suggestion = runner.invoke(
            cli.app, ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(no_suggestion_port), "--json"]
        )
        no_suggestion_plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(no_suggestion_port)])
    finally:
        occupied_again.close()
    no_suggestion_payload = json.loads(no_suggestion.stdout)
    assert (
        no_suggestion_payload["web"]["suggested_port"],
        no_suggestion_payload["web"]["suggested_start_command"],
        no_suggestion_payload["next_action_items"][-1]["kind"],
    ) == (None, "", "resolve_web_port")
    assert "suggested Web:" not in no_suggestion_plain.stdout
    assert "stop the existing service or choose another --web-port / serve --port value" in no_suggestion_plain.stdout


def test_cli_diagnose_doctor_network_web_requires_auth_before_start_guidance(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port("0.0.0.0")
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, result_error_text(install)

    result = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "0.0.0.0", "--web-port", str(web_port), "--json"],
    )
    plain = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "0.0.0.0", "--web-port", str(web_port)],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready_with_warnings"
    assert payload["strict_ready"] is False
    assert payload["web"]["auth_required"] is True
    assert payload["web"]["auth_token_configured"] is False
    assert payload["web"]["start_available"] is False
    assert payload["web"]["start_blocked_reason"] == "auth_required"
    assert payload["next_action_items"][-1]["kind"] == "configure_web_auth"
    assert payload["next_action_items"][-1]["command"] == payload["web"]["auth_start_command"]
    assert payload["next_action_items"][-1]["unsafe_command"] == payload["web"]["unsafe_start_command"]
    assert "--auth-token '<token>'" in payload["web"]["auth_start_command"]

    assert plain.exit_code == 0, plain.stdout
    assert f"web: http://127.0.0.1:{web_port} (auth required; non-loopback requires token or explicit unsafe opt-in)" in plain.stdout
    assert f"web start requires auth: {payload['web']['auth_start_command']}" in plain.stdout
    assert f"web start unsafe opt-in: {payload['web']['unsafe_start_command']}" in plain.stdout
    assert f"web start: loopora serve --open --host 0.0.0.0 --port {web_port}" not in plain.stdout
    assert "Set a Web auth token before starting network Web:" in plain.stdout


def test_cli_diagnose_doctor_network_web_uses_configured_auth_token_without_printing_it(tmp_path: Path) -> None:
    runner = CliRunner()
    web_port = _free_local_port("0.0.0.0")
    secret = "secret-token-123"
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)], env={APP_AUTH_ENV: secret})
    assert install.exit_code == 0, result_error_text(install)

    result = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "0.0.0.0", "--web-port", str(web_port), "--json"],
        env={APP_AUTH_ENV: secret},
    )
    plain = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(tmp_path), "--web-host", "0.0.0.0", "--web-port", str(web_port)],
        env={APP_AUTH_ENV: secret},
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    encoded = json.dumps(payload)
    assert payload["status"] == "ready"
    assert payload["web"]["auth_required"] is True
    assert payload["web"]["auth_token_configured"] is True
    assert payload["web"]["auth_token_env_var"] == APP_AUTH_ENV
    assert payload["web"]["auth_token_printed"] is False
    assert payload["web"]["start_available"] is True
    assert payload["next_action_items"][-1]["kind"] == "start_web"
    assert secret not in encoded
    assert secret not in plain.stdout
    assert f"web auth: {APP_AUTH_ENV} is configured in this shell; keep it set when running web start." in plain.stdout
    assert "web start:" in plain.stdout
    assert "web start requires auth:" not in plain.stdout


def test_first_use_support_route_is_read_only_exit_not_setup_gate() -> None:
    from loopora.first_use_route_readiness import FirstUseRouteReadinessGate, first_use_route_action_with_readiness

    gate = FirstUseRouteReadinessGate(
        setup_ready=False,
        setup_blockers=["review_inputs_required", "target_project_unready", "prefer_direct_path"],
        fit_review_required=True,
        first_task_ready=False,
        app_state_blockers=["app_state_not_ready"],
    )
    support = first_use_route_action_with_readiness({"kind": "support", "command": "loopora support --workdir /tmp/missing-project"}, gate=gate)
    placeholder_gate = FirstUseRouteReadinessGate(
        setup_ready=False,
        setup_blockers=["review_inputs_required", "target_project_required"],
        fit_review_required=True,
        first_task_ready=False,
        app_state_blockers=[],
    )
    placeholder = first_use_route_action_with_readiness({"kind": "support", "command": "loopora support --workdir '<project-dir>'"}, gate=placeholder_gate)
    assert (support["command_ready"], support["command_blockers"], placeholder["command_ready"], placeholder["command_blockers"]) == (
        True,
        [],
        False,
        ["target_project_required"],
    )
