from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli

from cli_bundle_commands_test_support import install_cli_bundle_service, write_cli_bundle


def _assert_resource_recovery_action_projection(payload: dict) -> None:
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["next_action_kinds"] == action_kinds
    assert payload["next_action_ready_now_kinds"] == action_kinds
    assert payload["next_action_ready_after_actions"] == {}


def test_cli_bundles_get_recovers_missing_identifier_without_service(monkeypatch) -> None:
    def fail_service():
        raise AssertionError("missing Plan File id recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, ["bundles", "get"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "missing_resource_identifier"
    assert payload["status"] == "blocked_by_missing_identifier"
    assert payload["required_identifier"] == "bundle_id"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "list_resources",
        "open_web_catalog",
        "retry_after_choice",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora bundles list" in payload["next_actions"][0]["command"]
    assert "loopora serve --open --workdir" in payload["next_actions"][1]["command"]
    assert payload["next_actions"][2]["command_template"] == "loopora bundles get <bundle-id>"


def test_cli_bundles_import_recovers_missing_plan_file_without_service(monkeypatch, tmp_path: Path) -> None:
    loopora_home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))

    def fail_service():
        raise AssertionError("missing Plan File path recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, ["bundles", "import"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "missing_plan_file_input"
    assert payload["status"] == "blocked_by_missing_plan_file"
    assert payload["required_identifier"] == "bundle_file"
    assert "reviewed Loop plan file" in payload["summary"]
    assert "does not create or review a new task" in payload["summary"]
    assert [item["kind"] for item in payload["next_actions"]] == [
        "retry_after_file_choice",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert payload["next_actions"][0]["command_template"].startswith(f"LOOPORA_HOME={loopora_home.resolve()} ")
    assert "loopora bundles import <plan-file>" in payload["next_actions"][0]["command_template"]
    assert payload["next_actions"][1]["command"].endswith("loopora start")
    assert payload["next_actions"][2]["command"].endswith("loopora fit")
    assert "loopora serve --open --workdir" in payload["next_actions"][3]["command"]


def test_cli_bundles_import_validates_plan_file_before_service(monkeypatch, tmp_path: Path) -> None:
    def fail_service():
        raise AssertionError("invalid Plan File input must be blocked before service or App state opens")

    monkeypatch.setattr(cli, "create_service", fail_service)
    missing_file = tmp_path / "missing-plan.yml"
    invalid_yaml = tmp_path / "invalid-plan.yml"
    invalid_yaml.write_text("metadata:\n  name: [\n", encoding="utf-8")

    missing = CliRunner().invoke(cli.app, ["bundles", "import", str(missing_file)])
    invalid = CliRunner().invoke(cli.app, ["bundles", "import", str(invalid_yaml)])

    for result in (missing, invalid):
        assert result.exit_code == 1
        assert "development_reset_required" not in result.stdout
        assert "Traceback" not in result.output
        assert "Usage:" not in result.output
        payload = json.loads(result.stdout)
        assert payload["resource_recovery"] == "invalid_plan_file_input"
        assert payload["status"] == "blocked_by_invalid_plan_file"
        assert payload["required_identifier"] == "bundle_file"
        assert payload["summary"].startswith("Import needs a readable reviewed Loop plan file")
        assert [item["kind"] for item in payload["next_actions"]] == [
            "choose_readable_plan_file",
            "repair_plan_file",
            "start_route_chooser",
        ]
        _assert_resource_recovery_action_projection(payload)

    assert json.loads(missing.stdout)["validation_error"] == "bundle file does not exist"
    assert "invalid bundle YAML" in json.loads(invalid.stdout)["validation_error"]


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
