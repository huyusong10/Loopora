from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service


def test_cli_bundles_delete_calls_service_boundary(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)
    runner = CliRunner()

    preview = runner.invoke(cli.app, ["bundles", "delete", "bundle_cli", "--dry-run"])
    result = runner.invoke(cli.app, ["bundles", "delete", "bundle_cli"])

    assert preview.exit_code == 0, preview.stdout
    assert result.exit_code == 0, result.stdout
    preview_payload = json.loads(preview.stdout)
    assert preview_payload["status"] == "dry_run"
    assert preview_payload["delete_allowed"] is True
    assert preview_payload["would_delete"] == {
        "bundle": "bundle_cli",
        "linked_loop": "loop_cli",
        "linked_orchestration": "orch_cli",
        "linked_role_definition_count": 2,
        "linked_role_definition_ids": ["role_builder", "role_gatekeeper"],
        "linked_run_count": 1,
        "linked_run_ids": ["run_cli"],
    }
    assert preview_payload["does_not_delete"] == [
        "original_exported_yaml_file",
        "source_project_workdir",
        "non_bundle_owned_assets",
        "external_provider_history",
    ]
    assert (preview_payload["next_action_kinds"], preview_payload["next_action_ready_now_kinds"], preview_payload["next_action_ready_after_actions"]) == (
        ["delete_bundle"],
        ["delete_bundle"],
        {},
    )
    assert "loopora bundles delete bundle_cli" in preview_payload["next_actions"][0]["command"]
    assert calls["preview_delete"] == "bundle_cli"
    assert calls["delete"] == "bundle_cli"
