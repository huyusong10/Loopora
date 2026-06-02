from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service, write_cli_bundle


def test_cli_bundles_import_replaces_existing_bundle(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)
    bundle_path = tmp_path / "task-bundle.yml"
    write_cli_bundle(bundle_path, tmp_path / "workdir")

    result = CliRunner().invoke(
        cli.app,
        ["bundles", "import", str(bundle_path), "--replace-bundle-id", "bundle_old"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["import"] == {"path": str(bundle_path), "replace_bundle_id": "bundle_old"}
