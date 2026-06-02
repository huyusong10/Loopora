from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service


def test_cli_bundles_derive_projects_bundle_yaml(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli.app,
        ["bundles", "derive", "loop_saved", "--name", "Derived CLI Bundle"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["derive"]["loop_id"] == "loop_saved"
    assert calls["derive"]["name"] == "Derived CLI Bundle"
    assert "Derived CLI Bundle" in result.stdout
