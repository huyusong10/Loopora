from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_first_use_docs_test_support import assert_cli_agent_entry_help, assert_cli_bundle_import_help, result_error_text


def _entry(payload: dict, adapter: str) -> dict:
    for item in payload["agent_entries"]:
        if item["adapter"] == adapter:
            return item
    raise AssertionError(f"missing adapter entry: {adapter}")


def test_cli_help_keeps_first_use_language_on_plan_files() -> None:
    runner = CliRunner()

    root_help = runner.invoke(cli.app, ["--help"])
    normalized_root_help = re.sub(r"\s+", " ", root_help.stdout)
    assert root_help.exit_code == 0, result_error_text(root_help)
    assert "Import, export, and manage Loop plan files" in root_help.stdout
    assert "Install /loopora-plan and /loopora-run project entries" in root_help.stdout
    assert "task goal, fake-done risk, and required evidence" in normalized_root_help
    assert "loopora doctor" in normalized_root_help
    assert "Report local first-use readiness" in root_help.stdout
    assert "Remove Loopora-managed Coding Agent project entries" in root_help.stdout
    assert "Internal runtime used by /loopora-plan and /loopora-run" in root_help.stdout
    assert "project entries" in root_help.stdout
    assert "Import and manage YAML bundles" not in root_help.stdout
    assert "Coding Agent adapters" not in root_help.stdout

    assert_cli_agent_entry_help(runner)
    assert_cli_bundle_import_help(runner)


def test_cli_diagnose_doctor_before_install_reports_actionable_first_use(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--json"])

    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert next(iter(payload)) == "diagnose_doctor_summary"
    assert payload["schema_version"] == 1
    assert payload["status"] == "not_ready"
    assert payload["ready"] is False
    assert payload["workdir"] == str(tmp_path.resolve())
    assert payload["web"]["origin"] == "http://127.0.0.1:8742"
    assert payload["web"]["loopback"] is True
    assert payload["web"]["requires_token_when_non_loopback"] is True

    codex = _entry(payload, "codex")
    assert codex["ready"] is False
    assert codex["install_state"] == "not_installed"
    assert codex["details_are_expected"] is True
    assert codex["next_action"] == "install_agent_entry"
    assert "loopora init codex" in codex["commands"]["install"]
    assert "failed_checks" not in codex
    assert payload["recommended_adapter"] == "codex"
    assert any("loopora init codex" in step for step in payload["next_steps"])

    alias_result = runner.invoke(cli.app, ["diagnose", "doctor", "--workdir", str(tmp_path), "--json"])
    alias_payload = json.loads(alias_result.stdout)

    assert alias_result.exit_code == 1, alias_result.stdout
    assert alias_payload["diagnose_doctor_summary"] == payload["diagnose_doctor_summary"]

    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path)])
    assert plain.exit_code == 1, plain.stdout
    assert "Loopora doctor: not_ready" in plain.stdout
    assert "ready: no" in plain.stdout
    assert "agent entries:" in plain.stdout
    assert "loopora init codex" in plain.stdout


def test_cli_diagnose_doctor_ready_after_one_agent_entry_install(tmp_path: Path) -> None:
    runner = CliRunner()
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, install.stdout

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["ready"] is True
    assert payload["ready_adapter_count"] == 1
    assert payload["attention_adapter_count"] == 0

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
    assert any("/loopora-plan" in step for step in payload["next_steps"])
    assert any("/loopora-run" in step for step in payload["next_steps"])

    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path)])
    assert plain.exit_code == 0, plain.stdout
    assert "Loopora doctor: ready" in plain.stdout
    assert "ready: yes" in plain.stdout
    assert "/loopora-plan" in plain.stdout


def test_cli_doctor_is_visible_as_first_use_root_command() -> None:
    runner = CliRunner()

    help_result = runner.invoke(cli.app, ["--help"])
    doctor_help = runner.invoke(cli.app, ["doctor", "--help"])
    grouped_help = runner.invoke(cli.app, ["diagnose", "doctor", "--help"])
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)

    assert help_result.exit_code == 0, help_result.stdout
    assert "use `loopora doctor` to confirm local readiness" in normalized_help
    assert "│ doctor" in help_result.stdout
    assert help_result.stdout.index("│ init") < help_result.stdout.index("│ doctor") < help_result.stdout.index("│ serve")
    assert doctor_help.exit_code == 0, doctor_help.stdout
    assert "Report local first-use readiness" in doctor_help.stdout
    assert grouped_help.exit_code == 0, grouped_help.stdout
    assert "Report local first-use readiness" in grouped_help.stdout
