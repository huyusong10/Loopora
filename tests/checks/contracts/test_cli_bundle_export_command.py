from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service


def test_cli_bundles_export_writes_requested_output_path(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)
    export_path = tmp_path / "exported.yml"

    result = CliRunner().invoke(cli.app, ["bundles", "export", "bundle_cli", "--output", str(export_path)])

    assert result.exit_code == 0, result.stdout
    assert calls["write"] == {"bundle_id": "bundle_cli", "path": str(export_path)}
    assert export_path.read_text(encoding="utf-8").startswith("version: 1")
