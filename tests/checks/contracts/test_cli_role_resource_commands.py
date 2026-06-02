from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli


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

        def delete_role_definition(self, role_definition_id: str):
            calls["delete"] = role_definition_id
            return {"id": role_definition_id, "deleted": True}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    list_result = runner.invoke(cli.app, ["roles", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert "builtin:builder" in list_result.stdout

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

    delete_result = runner.invoke(cli.app, ["roles", "delete", "role_custom"])
    assert delete_result.exit_code == 0, delete_result.stdout
    assert calls["delete"] == "role_custom"
