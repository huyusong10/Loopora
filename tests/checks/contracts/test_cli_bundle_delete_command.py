from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service


def test_cli_bundles_delete_calls_service_boundary(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["bundles", "delete", "bundle_cli"])

    assert result.exit_code == 0, result.stdout
    assert calls["delete"] == "bundle_cli"
