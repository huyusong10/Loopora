from __future__ import annotations

from typer.testing import CliRunner

from loopora import cli

from cli_first_use_docs_test_support import assert_cli_agent_entry_help, assert_cli_bundle_import_help, result_error_text


def test_cli_help_keeps_first_use_language_on_plan_files() -> None:
    runner = CliRunner()

    root_help = runner.invoke(cli.app, ["--help"])
    assert root_help.exit_code == 0, result_error_text(root_help)
    assert "Import, export, and manage Loop plan files" in root_help.stdout
    assert "Install /loopora-plan and /loopora-run project entries" in root_help.stdout
    assert "task goal, fake-done risk, and required evidence" in root_help.stdout
    assert "Remove Loopora-managed Coding Agent project entries" in root_help.stdout
    assert "Internal runtime used by /loopora-plan and /loopora-run" in root_help.stdout
    assert "project entries" in root_help.stdout
    assert "Import and manage YAML bundles" not in root_help.stdout
    assert "Coding Agent adapters" not in root_help.stdout

    assert_cli_agent_entry_help(runner)
    assert_cli_bundle_import_help(runner)
