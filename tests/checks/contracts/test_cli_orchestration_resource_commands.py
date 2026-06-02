from __future__ import annotations

import json

from typer.testing import CliRunner

from loopora import cli


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

    delete_result = runner.invoke(cli.app, ["orchestrations", "delete", "orch_1"])
    assert delete_result.exit_code == 0, delete_result.stdout
    assert calls["delete"] == "orch_1"
