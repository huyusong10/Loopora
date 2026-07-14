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


def test_cli_role_prompt_file_recovery_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_role_commands.py").read_text(encoding="utf-8")
    recovery_source = (ROOT / "src" / "loopora" / "cli_role_prompt_file_recovery.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_role_prompt_file_recovery import" in commands_source
    assert "invalid_prompt_file_input" not in commands_source
    assert "def _role_prompt_file_retry_template" not in commands_source
    assert "def role_prompt_file_input_error" in recovery_source
    assert "def exit_with_role_prompt_file_recovery" in recovery_source
    assert "def _role_prompt_file_retry_template" in recovery_source
    assert "cli_role_prompt_file_recovery.py" in service_boundaries
    assert "cli_role_prompt_file_recovery.py" in contracts


def test_cli_role_resource_projection_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_role_commands.py").read_text(encoding="utf-8")
    projection_source = (ROOT / "src" / "loopora" / "cli_resource_projection.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_resource_projection import" in commands_source
    assert "def role_definition_list_rows" in projection_source
    assert "def project_role_definition_delete_preview" in projection_source
    assert "def _cli_role_definition_delete_next_actions" not in commands_source
    assert "project_resource_recovery_action_contract" not in commands_source
    assert "copyable_loopora_command" not in commands_source
    assert "cli_resource_projection.py" in service_boundaries
    assert "cli_resource_projection.py" in contracts


def test_cli_roles_help_keeps_reusable_roles_after_review() -> None:
    runner = CliRunner()

    group_help = runner.invoke(cli.app, ["roles", "--help"])
    create_help = runner.invoke(cli.app, ["roles", "create", "--help"])
    derive_help = runner.invoke(cli.app, ["roles", "derive", "--help"])
    update_help = runner.invoke(cli.app, ["roles", "update", "--help"])
    delete_help = runner.invoke(cli.app, ["roles", "delete", "--help"])

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
    assert "Role definitions are reusable execution/persona assets" in normalized_group
    assert "advanced workflow customization" in normalized_group
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
    assert "stable reusable responsibility" in normalized_group
    assert "Creates a reusable role asset" in normalized_create
    assert "reviewed responsibility and prompt boundary" in normalized_create
    assert "not the first step for a new task" in normalized_create
    assert "does not start a run" in normalized_create
    assert "Derive copies a built-in or custom role" in normalized_derive
    assert "does not update the source role, existing Loops, or any running work" in normalized_derive
    assert "Update edits one saved custom role asset" in normalized_update
    assert "Existing Loop definitions and runs keep the role contract" in normalized_update
    assert "Delete removes one saved custom role asset" in normalized_delete
    assert "does not remove built-in roles, rewrite existing Loops, or change run history" in normalized_delete
    assert "--dry-run to preview Flow references" in normalized_delete


@pytest.mark.parametrize(
    "case",
    [
        {"args": ["roles", "get"], "action": "get", "retry_template": "loopora roles get <role-definition-id>"},
        {"args": ["roles", "derive"], "action": "derive", "retry_template": "loopora roles derive <role-definition-id>"},
        {"args": ["roles", "update"], "action": "update", "retry_template": "loopora roles update <role-definition-id>"},
        {"args": ["roles", "delete"], "action": "delete", "retry_template": "loopora roles delete <role-definition-id> --dry-run"},
    ],
)
def test_cli_roles_selected_resource_commands_recover_when_identifier_is_missing(monkeypatch, case: dict) -> None:
    def fail_service():
        raise AssertionError("missing role id recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, case["args"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "missing_resource_identifier"
    assert payload["status"] == "blocked_by_missing_identifier"
    assert payload["action"] == case["action"]
    assert payload["required_identifier"] == "role_definition_id"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "list_resources",
        "open_web_catalog",
        "retry_after_choice",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora roles list" in payload["next_actions"][0]["command"]
    assert "loopora serve --open --workdir" in payload["next_actions"][1]["command"]
    assert payload["next_actions"][2]["command_template"] == case["retry_template"]


def test_cli_roles_create_recovers_when_name_is_missing(monkeypatch) -> None:
    def fail_service():
        raise AssertionError("missing role name recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    for args in (["roles", "create"], ["roles", "create", "--name", ""]):
        result = CliRunner().invoke(cli.app, args)

        assert result.exit_code == 1
        assert "Missing option" not in result.output
        assert "Usage:" not in result.output
        payload = json.loads(result.stdout)
        assert payload["resource_recovery"] == "missing_resource_name"
        assert payload["status"] == "blocked_by_missing_name"
        assert payload["resource"] == "role definition"
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
        assert "loopora roles create --name '<role-name>'" in payload["next_actions"][0]["command_template"]
        assert "loopora roles list" in payload["next_actions"][1]["command"]
        assert "loopora serve --open --workdir" in payload["next_actions"][2]["command"]
        assert "loopora start" in payload["next_actions"][3]["command"]
        assert "loopora fit" in payload["next_actions"][4]["command"]


def test_cli_roles_list_get_create_update_derive_and_delete(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    prompt_path = tmp_path / "builder.md"
    prompt_path.write_text("---\nversion: 1\narchetype: builder\n---\nBuilder body\n", encoding="utf-8")

    current = {
        "id": "role_custom",
        "name": "Custom Builder",
        "description": "Saved builder",
        "archetype": "builder",
        "prompt_ref": "custom-builder.md",
        "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\nCurrent builder body\n",
        "executor_kind": "codex",
        "executor_mode": "preset",
        "command_cli": "codex",
        "command_args_text": "",
        "model": "gpt-5.4-mini",
        "reasoning_effort": "medium",
    }

    class FakeService:
        def list_role_definitions(self):
            return [
                {"id": "builtin:builder", "name": "Builder", "source": "builtin", "archetype": "builder", "executor_kind": "codex"},
                {"id": "role_custom", "name": "Custom Builder", "source": "custom", "archetype": "builder", "executor_kind": "codex"},
            ]

        def get_role_definition(self, role_definition_id: str):
            calls.setdefault("get_ids", []).append(role_definition_id)
            if role_definition_id == "builtin:builder":
                return {
                    "id": "builtin:builder",
                    "name": "Builder",
                    "description": "Built-in",
                    "archetype": "builder",
                    "prompt_ref": "builder.md",
                    "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\nBuiltin builder body\n",
                    "executor_kind": "codex",
                    "executor_mode": "preset",
                    "command_cli": "codex",
                    "command_args_text": "",
                    "model": "gpt-5.4",
                    "reasoning_effort": "medium",
                }
            return current

        def create_role_definition(self, **kwargs):
            calls.setdefault("create", []).append(kwargs)
            return {"id": "role_new", **kwargs}

        def update_role_definition(self, role_definition_id: str, **kwargs):
            calls["update"] = (role_definition_id, kwargs)
            return {"id": role_definition_id, **kwargs}

        def preview_role_definition_delete(self, role_definition_id: str):
            calls["preview_delete"] = role_definition_id
            return {
                "status": "dry_run",
                "dry_run": True,
                "delete_allowed": True,
                "would_delete": {
                    "role_definition": role_definition_id,
                    "referencing_orchestration_count": 0,
                    "referencing_orchestration_ids": [],
                },
                "does_not_delete": ["saved_orchestration_snapshots"],
            }

        def delete_role_definition(self, role_definition_id: str):
            calls["delete"] = role_definition_id
            return {"id": role_definition_id, "deleted": True}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    list_result = runner.invoke(cli.app, ["roles", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert "builtin:builder" in list_result.stdout

    list_json_result = runner.invoke(cli.app, ["roles", "list", "--json"])
    assert list_json_result.exit_code == 0, list_json_result.stdout
    list_payload = json.loads(list_json_result.stdout)
    assert list_payload["status"] == "ok"
    assert list_payload["count"] == 2
    assert [item["id"] for item in list_payload["role_definitions"]] == ["builtin:builder", "role_custom"]
    assert "archetype=" not in list_json_result.stdout

    get_result = runner.invoke(cli.app, ["roles", "get", "role_custom"])
    assert get_result.exit_code == 0, get_result.stdout
    assert json.loads(get_result.stdout)["id"] == "role_custom"

    create_result = runner.invoke(cli.app, ["roles", "create", "--name", "New Builder", "--archetype", "builder", "--prompt-file", str(prompt_path)])
    assert create_result.exit_code == 0, create_result.stdout
    assert calls["create"][0]["name"] == "New Builder"
    assert "Builder body" in calls["create"][0]["prompt_markdown"]

    update_result = runner.invoke(cli.app, ["roles", "update", "role_custom", "--name", "Updated Builder", "--prompt-file", str(prompt_path)])
    assert update_result.exit_code == 0, update_result.stdout
    update_id, update_kwargs = calls["update"]
    assert update_id == "role_custom"
    assert update_kwargs["name"] == "Updated Builder"
    assert update_kwargs["prompt_ref"] == "custom-builder.md"

    derive_result = runner.invoke(cli.app, ["roles", "derive", "builtin:builder", "--name", "Derived Builder"])
    assert derive_result.exit_code == 0, derive_result.stdout
    assert calls["create"][-1]["name"] == "Derived Builder"
    assert calls["create"][-1]["archetype"] == "builder"

    preview_result = runner.invoke(cli.app, ["roles", "delete", "role_custom", "--dry-run"])
    assert preview_result.exit_code == 0, preview_result.stdout
    preview_payload = json.loads(preview_result.stdout)
    assert preview_payload["delete_allowed"] is True
    assert preview_payload["would_delete"]["referencing_orchestration_count"] == 0
    assert preview_payload["next_actions"][0]["kind"] == "delete_role_definition"
    _assert_resource_recovery_action_projection(preview_payload)
    assert preview_payload["next_actions"][0]["command"].endswith("loopora roles delete role_custom")
    assert preview_payload["next_actions"][0]["note"] == "Run this only after reviewing the dry-run scope."
    assert calls["preview_delete"] == "role_custom"
    assert "delete" not in calls

    delete_result = runner.invoke(cli.app, ["roles", "delete", "role_custom"])
    assert delete_result.exit_code == 0, delete_result.stdout
    assert calls["delete"] == "role_custom"


def test_cli_roles_list_json_errors_are_structured(monkeypatch) -> None:
    class FailingService:
        def list_role_definitions(self):
            raise LooporaError("role list unavailable")

    monkeypatch.setattr(cli, "create_service", FailingService)

    result = CliRunner().invoke(cli.app, ["roles", "list", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"status": "error", "error": "role list unavailable"}
    assert result.stderr == ""


def test_cli_role_create_redacts_low_level_storage_errors(monkeypatch, tmp_path: Path) -> None:
    local_path = tmp_path / "private" / "roles.db"

    class FailingService:
        def create_role_definition(self, **_kwargs):
            raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(cli, "create_service", FailingService)

    result = CliRunner().invoke(cli.app, ["roles", "create", "--name", "New Builder"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload == {"status": "error", "error": "role definition could not be saved"}
    assert result.stderr == ""
    assert "permission denied" not in result.output
    assert str(local_path) not in result.output


@pytest.mark.parametrize(
    ("prompt_name", "prompt_state", "validation_error"),
    [
        ("missing-prompt.md", "missing", "prompt file does not exist"),
        ("prompt-dir", "directory", "prompt file could not be read"),
        ("invalid-prompt.md", "invalid_utf8", "prompt file must be UTF-8 encoded Markdown"),
    ],
)
def test_cli_role_create_reports_prompt_file_input_recovery_without_usage_or_local_path(
    tmp_path: Path,
    prompt_name: str,
    prompt_state: str,
    validation_error: str,
) -> None:
    prompt_path = tmp_path / prompt_name
    if prompt_state == "directory":
        prompt_path.mkdir()
    elif prompt_state == "invalid_utf8":
        prompt_path.write_bytes(b"\xff")

    result = CliRunner().invoke(
        cli.app,
        ["roles", "create", "--name", "New Builder", "--archetype", "builder", "--prompt-file", str(prompt_path)],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_prompt_file_input"
    assert payload["status"] == "blocked_by_prompt_file"
    assert payload["resource"] == "Strategy Source prompt file"
    assert payload["action"] == "create"
    assert payload["validation_error"] == validation_error
    assert [item["kind"] for item in payload["next_actions"]] == [
        "repair_prompt_file",
        "choose_prompt_file",
        "validate_prompt_file",
        "list_prompt_templates",
        "render_prompt_template",
        "start_route_chooser",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora roles create --name '<role-name>' --prompt-file <prompt-file>" in payload["next_actions"][1]["command_template"]
    assert "loopora prompts validate <prompt-file>" in payload["next_actions"][2]["command_template"]
    assert "loopora prompts list" in payload["next_actions"][3]["command"]
    assert "loopora prompts template <prompt-ref>" in payload["next_actions"][4]["command_template"]
    assert "loopora start" in payload["next_actions"][5]["command"]
    assert result.stderr == ""
    assert str(prompt_path) not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
