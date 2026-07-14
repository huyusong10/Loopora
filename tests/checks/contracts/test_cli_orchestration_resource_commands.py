from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.service_types import LooporaError


ROOT = Path(__file__).resolve().parents[3]


def _assert_resource_recovery_action_projection(payload: dict) -> None:
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["next_action_kinds"] == action_kinds
    assert payload["next_action_ready_now_kinds"] == action_kinds
    assert payload["next_action_ready_after_actions"] == {}


def _assert_strategy_source_file_recovery(result, *, action: str, validation_error: str, hidden_text: str = "") -> dict:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_strategy_source_file_input"
    assert payload["status"] == "blocked_by_strategy_source_file"
    assert payload["resource"] == "Strategy Source file"
    assert payload["action"] == action
    assert payload["validation_error"] == validation_error
    assert [item["kind"] for item in payload["next_actions"]] == [
        "repair_strategy_source_file",
        "choose_strategy_source_file",
        "choose_workflow_preset",
        "start_route_chooser",
        "check_fit_first",
    ]
    _assert_resource_recovery_action_projection(payload)
    if action == "update":
        strategy_template = "loopora orchestrations update <flow-id> --strategy-file <strategy-file>"
        preset_template = "loopora orchestrations update <flow-id> --workflow-preset <preset>"
    elif action == "derive":
        strategy_template = "loopora orchestrations derive <flow-id> --name '<flow-name>' --strategy-file <strategy-file>"
        preset_template = "loopora orchestrations derive <flow-id> --name '<flow-name>' --workflow-preset <preset>"
    else:
        strategy_template = "loopora orchestrations create --name '<flow-name>' --strategy-file <strategy-file>"
        preset_template = "loopora orchestrations create --name '<flow-name>' --workflow-preset <preset>"
    assert strategy_template in payload["next_actions"][1]["command_template"]
    assert preset_template in payload["next_actions"][2]["command_template"]
    assert "loopora start" in payload["next_actions"][3]["command"]
    assert "loopora fit" in payload["next_actions"][4]["command"]
    assert result.stderr == ""
    if hidden_text:
        assert hidden_text not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    return payload


def test_cli_orchestration_strategy_file_recovery_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_orchestration_commands.py").read_text(encoding="utf-8")
    recovery_source = (ROOT / "src" / "loopora" / "cli_orchestration_strategy_file_recovery.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_orchestration_strategy_file_recovery import" in commands_source
    assert "invalid_strategy_source_file_input" not in commands_source
    assert "_orchestration_strategy_file_retry_template" not in commands_source
    assert "_orchestration_preset_retry_template" not in commands_source
    assert "exit_with_orchestration_strategy_file_recovery" in recovery_source
    assert "_orchestration_strategy_file_retry_template" in recovery_source
    assert "_orchestration_preset_retry_template" in recovery_source
    assert "cli_orchestration_strategy_file_recovery.py" in service_boundaries
    assert "cli_orchestration_strategy_file_recovery.py" in contracts


def test_cli_orchestration_resource_projection_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_orchestration_commands.py").read_text(encoding="utf-8")
    projection_source = (ROOT / "src" / "loopora" / "cli_resource_projection.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_resource_projection import" in commands_source
    assert "def orchestration_list_rows" in projection_source
    assert "def project_orchestration_delete_preview" in projection_source
    assert "def _cli_orchestration_delete_next_actions" not in commands_source
    assert "project_resource_recovery_action_contract" not in commands_source
    assert "copyable_loopora_command" not in commands_source
    assert "cli_resource_projection.py" in service_boundaries
    assert "cli_resource_projection.py" in contracts


def test_cli_orchestrations_help_keeps_reusable_flows_after_review() -> None:
    runner = CliRunner()

    group_help = runner.invoke(cli.app, ["orchestrations", "--help"])
    create_help = runner.invoke(cli.app, ["orchestrations", "create", "--help"])
    derive_help = runner.invoke(cli.app, ["orchestrations", "derive", "--help"])
    update_help = runner.invoke(cli.app, ["orchestrations", "update", "--help"])
    delete_help = runner.invoke(cli.app, ["orchestrations", "delete", "--help"])

    normalized_group = " ".join(group_help.stdout.split())
    normalized_create = " ".join(create_help.stdout.split())
    normalized_derive = " ".join(derive_help.stdout.split())
    normalized_update = " ".join(update_help.stdout.split())
    normalized_delete = " ".join(delete_help.stdout.split())
    assert group_help.exit_code == 0, group_help.stdout
    assert create_help.exit_code == 0, create_help.stdout
    assert derive_help.exit_code == 0, derive_help.stdout
    assert update_help.exit_code == 0, update_help.stdout
    assert delete_help.exit_code == 0, delete_help.stdout
    assert "Orchestrations are reusable run-flow assets" in normalized_group
    assert "customize or share the reviewed workflow" in normalized_group
    assert "run `loopora start` first" in normalized_group
    assert "use `loopora fit` when fit is uncertain" in normalized_group
    assert "Fit Guide/Web choices path" in normalized_group
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in normalized_group
    assert "same-Agent path" in normalized_group
    assert 'loopora init <agent> --workdir "$PWD"' in normalized_group
    assert 'loopora doctor --workdir "$PWD"' in normalized_group
    assert normalized_group.index("Fit Guide/Web choices path") < normalized_group.index("same-Agent path")
    assert normalized_group.index("same-Agent path") < normalized_group.index("/loopora-plan")
    assert "Builder -> Inspector/Guide -> GateKeeper" in normalized_group
    assert "/loopora-plan" in normalized_group
    assert "before creating custom flows" in normalized_group
    assert "Creates a reusable workflow asset" in normalized_create
    assert "after the desired workflow shape has been reviewed" in normalized_create
    assert "not required for first use" in normalized_create
    assert "does not start a run" in normalized_create
    assert "Derive copies a built-in or custom orchestration" in normalized_derive
    assert "does not update the source orchestration, existing Loops, or any running work" in normalized_derive
    assert "Update edits one saved custom flow" in normalized_update
    assert "Existing Loop definitions and runs keep the strategy source" in normalized_update
    assert "Delete removes one saved custom flow" in normalized_delete
    assert "does not remove built-in flows, rewrite existing Loops, or change run history" in normalized_delete
    assert "--dry-run to preview Loop references" in normalized_delete


@pytest.mark.parametrize(
    "case",
    [
        {"args": ["orchestrations", "get"], "action": "get", "retry_template": "loopora orchestrations get <flow-id>"},
        {"args": ["orchestrations", "derive"], "action": "derive", "retry_template": "loopora orchestrations derive <flow-id>"},
        {"args": ["orchestrations", "update"], "action": "update", "retry_template": "loopora orchestrations update <flow-id>"},
        {"args": ["orchestrations", "delete"], "action": "delete", "retry_template": "loopora orchestrations delete <flow-id> --dry-run"},
    ],
)
def test_cli_orchestrations_selected_resource_commands_recover_when_identifier_is_missing(
    monkeypatch,
    case: dict,
) -> None:
    def fail_service():
        raise AssertionError("missing Flow id recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, case["args"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "missing_resource_identifier"
    assert payload["status"] == "blocked_by_missing_identifier"
    assert payload["action"] == case["action"]
    assert payload["required_identifier"] == "orchestration_id"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "list_resources",
        "open_web_catalog",
        "retry_after_choice",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora orchestrations list" in payload["next_actions"][0]["command"]
    assert "loopora serve --open --workdir" in payload["next_actions"][1]["command"]
    assert payload["next_actions"][2]["command_template"] == case["retry_template"]


def test_cli_orchestrations_create_recovers_when_name_is_missing(monkeypatch) -> None:
    def fail_service():
        raise AssertionError("missing Flow name recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    for args in (["orchestrations", "create"], ["orchestrations", "create", "--name", ""]):
        result = CliRunner().invoke(cli.app, args)

        assert result.exit_code == 1
        assert "Missing option" not in result.output
        assert "Usage:" not in result.output
        payload = json.loads(result.stdout)
        assert payload["resource_recovery"] == "missing_resource_name"
        assert payload["status"] == "blocked_by_missing_name"
        assert payload["resource"] == "Flow"
        assert payload["action"] == "create"
        assert payload["required_identifier"] == "name"
        assert [item["kind"] for item in payload["next_actions"]] == [
            "retry_after_name_choice",
            "list_resources",
            "open_web_catalog",
            "start_route_chooser",
            "check_fit_first",
        ]
        _assert_resource_recovery_action_projection(payload)
        assert "loopora orchestrations create --name '<flow-name>'" in payload["next_actions"][0]["command_template"]
        assert "loopora orchestrations list" in payload["next_actions"][1]["command"]
        assert "loopora serve --open --workdir" in payload["next_actions"][2]["command"]
        assert "loopora start" in payload["next_actions"][3]["command"]
        assert "loopora fit" in payload["next_actions"][4]["command"]


def test_cli_orchestrations_create_and_list(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeService:
        def create_orchestration(self, **kwargs):
            calls["create_orchestration"] = kwargs
            return {"id": "orch_1", "name": kwargs["name"], "workflow_json": {"roles": [], "steps": []}}

        def list_orchestrations(self):
            return [
                {"id": "builtin:build_first", "name": "Build First", "source": "builtin", "workflow_json": {"roles": [1], "steps": [1]}},
                {"id": "orch_1", "name": "Custom", "source": "custom", "workflow_json": {"roles": [1, 2], "steps": [1, 2]}},
            ]

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    create_result = runner.invoke(cli.app, ["orchestrations", "create", "--name", "Custom", "--workflow-preset", "inspect_first"])
    assert create_result.exit_code == 0, create_result.stdout
    assert calls["create_orchestration"]["name"] == "Custom"
    assert calls["create_orchestration"]["strategy_source"] == {"preset": "inspect_first"}

    list_result = runner.invoke(cli.app, ["orchestrations", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert "builtin:build_first" in list_result.stdout
    assert "orch_1" in list_result.stdout

    list_json_result = runner.invoke(cli.app, ["orchestrations", "list", "--json"])
    assert list_json_result.exit_code == 0, list_json_result.stdout
    list_payload = json.loads(list_json_result.stdout)
    assert list_payload["status"] == "ok"
    assert list_payload["count"] == 2
    assert [item["id"] for item in list_payload["orchestrations"]] == ["builtin:build_first", "orch_1"]
    assert "source=" not in list_json_result.stdout


def test_cli_orchestrations_list_json_errors_are_structured(monkeypatch) -> None:
    class FailingService:
        def list_orchestrations(self):
            raise LooporaError("orchestration list unavailable")

    monkeypatch.setattr(cli, "create_service", FailingService)

    result = CliRunner().invoke(cli.app, ["orchestrations", "list", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"status": "error", "error": "orchestration list unavailable"}
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("strategy_name", "strategy_state", "validation_error"),
    [
        ("missing-strategy.yml", "missing", "strategy source file does not exist"),
        ("strategy-dir", "directory", "strategy source file could not be read"),
        ("invalid-strategy.yml", "invalid_utf8", "workflow file must be UTF-8 encoded YAML or JSON"),
    ],
)
def test_cli_orchestrations_create_reports_strategy_file_input_recovery_before_service(
    monkeypatch,
    tmp_path,
    strategy_name: str,
    strategy_state: str,
    validation_error: str,
) -> None:
    def fail_service():
        raise AssertionError("strategy file preflight must not require App state")

    monkeypatch.setattr(cli, "create_service", fail_service)
    strategy_file = tmp_path / strategy_name
    if strategy_state == "directory":
        strategy_file.mkdir()
    elif strategy_state == "invalid_utf8":
        strategy_file.write_bytes(b"\xff")

    result = CliRunner().invoke(
        cli.app,
        ["orchestrations", "create", "--name", "Custom", "--strategy-file", str(strategy_file)],
    )

    _assert_strategy_source_file_recovery(
        result,
        action="create",
        validation_error=validation_error,
        hidden_text=str(strategy_file),
    )


def test_cli_orchestrations_create_expands_home_strategy_file(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    strategy_file = home_dir / "strategy.yml"
    strategy_file.write_text("roles: []\nsteps: []\n", encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeService:
        def create_orchestration(self, **kwargs):
            calls["create_orchestration"] = kwargs
            return {"id": "orch_1", "name": kwargs["name"], "strategy_source": kwargs["strategy_source"]}

    monkeypatch.setattr(cli, "create_service", FakeService)

    result = CliRunner().invoke(
        cli.app,
        ["orchestrations", "create", "--name", "Custom", "--strategy-file", "~/strategy.yml"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_orchestration"]["strategy_source"] == {"roles": [], "steps": []}


def test_cli_orchestrations_update_and_derive_prevalidate_strategy_file_before_service(monkeypatch, tmp_path) -> None:
    def fail_service():
        raise AssertionError("strategy file preflight must not require saved Flow lookup")

    monkeypatch.setattr(cli, "create_service", fail_service)
    strategy_file = tmp_path / "missing-strategy.yml"
    runner = CliRunner()

    for args, action in (
        (["orchestrations", "update", "orch_1", "--strategy-file", str(strategy_file)], "update"),
        (["orchestrations", "derive", "orch_1", "--strategy-file", str(strategy_file)], "derive"),
    ):
        result = runner.invoke(cli.app, args)
        _assert_strategy_source_file_recovery(
            result,
            action=action,
            validation_error="strategy source file does not exist",
            hidden_text=str(strategy_file),
        )


def test_cli_orchestration_create_redacts_low_level_storage_errors(monkeypatch, tmp_path) -> None:
    local_path = tmp_path / "private" / "orchestrations.db"

    class FailingService:
        def create_orchestration(self, **_kwargs):
            raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(cli, "create_service", FailingService)

    result = CliRunner().invoke(cli.app, ["orchestrations", "create", "--name", "Custom"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"status": "error", "error": "orchestration could not be saved"}
    assert result.stderr == ""
    assert "permission denied" not in result.output
    assert str(local_path) not in result.output


def test_cli_orchestrations_get_update_derive_and_delete(monkeypatch) -> None:
    calls: dict[str, object] = {}

    current = {
        "id": "orch_1",
        "name": "Current",
        "description": "Saved orchestration",
        "workflow_json": {"preset": "inspect_first"},
        "prompt_files_json": {"builder.md": "---\nversion: 1\narchetype: builder\n---\nBuilder body\n"},
        "role_models_json": {"builder": "gpt-5.4-mini"},
    }

    class FakeService:
        def get_orchestration(self, orchestration_id: str):
            calls.setdefault("get_ids", []).append(orchestration_id)
            if orchestration_id == "builtin:build_first":
                return {
                    "id": "builtin:build_first",
                    "name": "Build First",
                    "description": "Built-in",
                    "workflow_json": {"preset": "build_first"},
                    "prompt_files_json": {},
                    "role_models_json": {},
                }
            return current

        def update_orchestration(self, orchestration_id: str, **kwargs):
            calls["update"] = (orchestration_id, kwargs)
            return {"id": orchestration_id, **kwargs, "workflow_json": kwargs["strategy_source"]}

        def create_orchestration(self, **kwargs):
            calls.setdefault("create", []).append(kwargs)
            return {"id": "orch_new", **kwargs, "workflow_json": kwargs["strategy_source"]}

        def preview_orchestration_delete(self, orchestration_id: str):
            calls["preview_delete"] = orchestration_id
            return {
                "status": "dry_run",
                "dry_run": True,
                "delete_allowed": True,
                "would_delete": {
                    "orchestration": orchestration_id,
                    "referencing_loop_count": 0,
                    "referencing_loop_ids": [],
                },
                "does_not_delete": ["saved_loop_snapshots"],
            }

        def delete_orchestration(self, orchestration_id: str):
            calls["delete"] = orchestration_id
            return {"id": orchestration_id, "deleted": True}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    get_result = runner.invoke(cli.app, ["orchestrations", "get", "orch_1"])
    assert get_result.exit_code == 0, get_result.stdout
    assert json.loads(get_result.stdout)["id"] == "orch_1"

    update_result = runner.invoke(cli.app, ["orchestrations", "update", "orch_1", "--name", "Updated", "--workflow-preset", "repair_loop"])
    assert update_result.exit_code == 0, update_result.stdout
    update_id, update_kwargs = calls["update"]
    assert update_id == "orch_1"
    assert update_kwargs["name"] == "Updated"
    assert update_kwargs["strategy_source"] == {"preset": "repair_loop"}

    derive_result = runner.invoke(cli.app, ["orchestrations", "derive", "builtin:build_first", "--name", "Derived"])
    assert derive_result.exit_code == 0, derive_result.stdout
    assert calls["create"][-1]["name"] == "Derived"
    assert calls["create"][-1]["strategy_source"] == {"preset": "build_first"}

    preview_result = runner.invoke(cli.app, ["orchestrations", "delete", "orch_1", "--dry-run"])
    assert preview_result.exit_code == 0, preview_result.stdout
    preview_payload = json.loads(preview_result.stdout)
    assert preview_payload["delete_allowed"] is True
    assert preview_payload["would_delete"]["referencing_loop_count"] == 0
    assert preview_payload["next_actions"][0]["kind"] == "delete_orchestration"
    _assert_resource_recovery_action_projection(preview_payload)
    assert preview_payload["next_actions"][0]["command"].endswith("loopora orchestrations delete orch_1")
    assert preview_payload["next_actions"][0]["note"] == "Run this only after reviewing the dry-run scope."
    assert calls["preview_delete"] == "orch_1"
    assert "delete" not in calls

    delete_result = runner.invoke(cli.app, ["orchestrations", "delete", "orch_1"])
    assert delete_result.exit_code == 0, delete_result.stdout
    assert calls["delete"] == "orch_1"
