from __future__ import annotations

import json
from pathlib import Path
import shlex

import pytest
import yaml
from typer.testing import CliRunner

from loopora import cli
from db_test_support import _read_service_log_records


def _assert_loop_recovery_action_projection(payload: dict) -> None:
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["next_action_kinds"] == action_kinds
    assert payload["next_action_ready_now_kinds"] == action_kinds
    assert payload["next_action_ready_after_actions"] == {}


def test_cli_loop_creation_emits_structured_logs(monkeypatch, tmp_path: Path) -> None:
    spec_path, workdir = write_loop_create_inputs(tmp_path)
    install_loop_create_service(monkeypatch, loop_id="loop_logged")

    result = invoke_loop_create(spec_path, workdir, "--name", "Logged Loop")

    assert result.exit_code == 0, result.stdout
    records = _read_service_log_records()
    created_record = next(item for item in records if item["event"] == "cli.loop.create.completed")
    assert created_record["loop_id"] == "loop_logged"
    assert created_record["context"]["start"] is False


def test_cli_loop_create_expands_home_spec_and_workdir_before_service(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    spec_path = home_dir / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = home_dir / "project"
    workdir.mkdir()
    calls = install_loop_create_service(monkeypatch, loop_id="loop_home")

    result = CliRunner().invoke(
        cli.app,
        ["loops", "create", "--spec", "~/spec.md", "--workdir", "~/project"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["spec_path"] == spec_path.resolve()
    assert calls["create_loop"]["workdir"] == workdir.resolve()


@pytest.mark.parametrize("strategy_file_flag", ["--workflow-file", "--strategy-file"])
def test_cli_loop_create_accepts_parallel_strategy_file(strategy_file_flag: str, monkeypatch, tmp_path: Path) -> None:
    spec_path, workdir = write_loop_create_inputs(tmp_path)
    workflow_path = tmp_path / "workflow.yml"
    workflow_path.write_text(yaml.safe_dump(parallel_strategy_source(), sort_keys=False), encoding="utf-8")
    calls = install_loop_create_service(monkeypatch, loop_id="loop_parallel")

    result = invoke_loop_create(spec_path, workdir, strategy_file_flag, str(workflow_path))

    assert result.exit_code == 0, result.stdout
    workflow = calls["create_loop"]["workflow"]
    assert workflow["steps"][1]["parallel_group"] == "inspection_pack"
    assert workflow["steps"][1]["inputs"]["evidence_query"]["archetypes"] == ["builder"]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "contract_inspection_step",
        "evidence_inspection_step",
    ]
    assert workflow["controls"][0]["when"]["signal"] == "no_evidence_progress"
    assert workflow["controls"][0]["call"]["role_id"] == "evidence_inspector"


@pytest.mark.parametrize(
    ("command_args", "action", "retry_kind"),
    [
        (["loops", "create"], "create", "retry_loop_create"),
        (["run"], "run", "retry_loop_run"),
    ],
)
def test_cli_loop_compose_reports_missing_strategy_file_before_app_state(
    monkeypatch,
    tmp_path: Path,
    command_args: list[str],
    action: str,
    retry_kind: str,
) -> None:
    spec_path, workdir = write_loop_create_inputs(tmp_path)
    strategy_file = tmp_path / "missing-strategy.yml"

    def fail_service():
        raise AssertionError("strategy file preflight must not require App state")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(
        cli.app,
        [
            *command_args,
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--strategy-file",
            str(strategy_file),
            "--json",
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["loop_recovery"] == "target_strategy_source_unavailable"
    assert payload["status"] == "blocked_by_strategy_source_file"
    assert payload["action"] == action
    assert payload["strategy_source_state"] == {
        "status": "unavailable",
        "error": "strategy source file does not exist",
    }
    assert [item["kind"] for item in payload["next_actions"]] == [
        "repair_strategy_source",
        "choose_strategy_source",
        "choose_workflow_preset",
        retry_kind,
    ]
    assert payload["next_actions"][0]["validation_error"] == "strategy source file does not exist"
    assert all("command" not in item and "command_template" not in item for item in payload["next_actions"])
    assert str(strategy_file) not in result.stdout
    assert "development_reset_required" not in result.stdout


@pytest.mark.parametrize(
    "case",
    [
        {
            "args": ["loops", "status"],
            "required_identifier": "loop_or_run_id",
            "required_label": "Loop ID or run ID",
            "retry_template": "loopora loops status <loop-or-run-id>",
            "expects_json": False,
        },
        {
            "args": ["loops", "stop", "--json"],
            "required_identifier": "run_id",
            "required_label": "Run ID",
            "retry_template": "loopora loops stop <run-id>",
            "expects_json": True,
        },
        {
            "args": ["loops", "rerun", "--json"],
            "required_identifier": "loop_id",
            "required_label": "Loop ID",
            "retry_template": "loopora loops rerun <loop-id>",
            "expects_json": True,
        },
        {
            "args": ["loops", "delete", "--dry-run"],
            "required_identifier": "loop_id",
            "required_label": "Loop ID",
            "retry_template": "loopora loops delete <loop-id> --dry-run",
            "expects_json": False,
        },
    ],
)
def test_cli_loop_existing_work_commands_recover_when_identifier_is_missing(
    monkeypatch,
    case: dict,
) -> None:
    def fail_service():
        raise AssertionError("missing identifier recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, case["args"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    if case["expects_json"]:
        payload = json.loads(result.stdout)
        assert payload["loop_recovery"] == "missing_loop_identifier"
        assert payload["status"] == "blocked_by_missing_identifier"
        assert payload["required_identifier"] == case["required_identifier"]
        assert payload["required_identifier_label"] == case["required_label"]
        assert [item["kind"] for item in payload["next_actions"]] == [
            "list_saved_loops",
            "open_web_saved_work",
            "retry_after_choice",
        ]
        _assert_loop_recovery_action_projection(payload)
        assert "loopora loops list" in payload["next_actions"][0]["command"]
        assert 'loopora serve --open --workdir "$PWD"' in payload["next_actions"][1]["command"]
        assert payload["next_actions"][2]["command_template"] == case["retry_template"]
        return
    assert "Loopora saved work needs an id" in result.output
    assert f"required identifier: {case['required_label']}" in result.output
    assert "loopora loops list" in result.output
    assert 'loopora serve --open --workdir "$PWD"' in result.output
    assert case["retry_template"] in result.output


def test_cli_loop_create_missing_spec_recovery_uses_effective_strategy_file(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    missing_spec = tmp_path / "missing-spec.md"
    strategy_file = tmp_path / "strategy.yml"
    write_minimal_strategy_file(strategy_file)

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("missing spec preflight must not create a loop")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--orchestration-id",
            "builtin:repair_loop",
            "--strategy-preset",
            "inspect_first",
            "--strategy-file",
            str(strategy_file),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    init_tokens = loopora_command_tokens(payload["next_actions"][0]["command"])
    retry_tokens = loopora_command_tokens(payload["next_actions"][1]["command"])
    assert option_value(init_tokens, "--strategy-file") == str(strategy_file.resolve(strict=False))
    assert option_value(retry_tokens, "--strategy-file") == str(strategy_file.resolve(strict=False))
    assert "--orchestration-id" not in init_tokens
    assert "--orchestration-id" not in retry_tokens
    assert "--strategy-preset" not in init_tokens
    assert "--strategy-preset" not in retry_tokens


def test_cli_loop_create_missing_spec_with_missing_strategy_file_avoids_dead_commands(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    missing_spec = tmp_path / "missing-spec.md"
    strategy_file = tmp_path / "missing-strategy.yml"

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("missing spec preflight must not create a loop")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--strategy-file",
            str(strategy_file),
            "--json",
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["spec_state"]["status"] == "missing"
    assert payload["spec_state"]["strategy_source_state"] == {
        "status": "unavailable",
        "error": "strategy source file does not exist",
    }
    assert [action["kind"] for action in payload["next_actions"]] == [
        "repair_strategy_source",
        "choose_spec",
        "retry_loop_create",
    ]
    assert "command" not in payload["next_actions"][0]
    assert "command" not in payload["next_actions"][2]
    assert "loopora spec init" not in result.stdout
    assert str(strategy_file) not in result.stdout


@pytest.mark.parametrize(
    ("command_args", "action", "retry_kind"),
    [
        (["loops", "create"], "create", "retry_loop_create"),
        (["run"], "run", "retry_loop_run"),
    ],
)
def test_cli_loop_compose_missing_workdir_with_missing_strategy_file_surfaces_both_blockers(
    monkeypatch,
    tmp_path: Path,
    command_args: list[str],
    action: str,
    retry_kind: str,
) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    missing_workdir = tmp_path / "missing-workdir"
    strategy_file = tmp_path / "missing-strategy.yml"

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("workdir preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"workdir preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            *command_args,
            "--spec",
            str(spec_path),
            "--workdir",
            str(missing_workdir),
            "--strategy-file",
            str(strategy_file),
            "--json",
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == action
    assert payload["workdir_state"]["status"] == "missing"
    assert payload["workdir_state"]["strategy_source_state"] == {
        "status": "unavailable",
        "error": "strategy source file does not exist",
    }
    assert [item["kind"] for item in payload["next_actions"]] == [
        "create_workdir",
        "repair_strategy_source",
        "confirm_readiness",
        retry_kind,
    ]
    assert payload["next_action_ready_now_kinds"] == ["create_workdir"]
    assert payload["next_action_ready_after_actions"] == {
        "repair_strategy_source": "create_workdir",
        "confirm_readiness": "repair_strategy_source",
        retry_kind: "confirm_readiness",
    }
    assert "mkdir -p" in payload["next_actions"][0]["command"]
    assert payload["next_actions"][1]["validation_error"] == "strategy source file does not exist"
    assert "command" not in payload["next_actions"][1]
    assert "loopora doctor --workdir" in payload["next_actions"][2]["command"]
    assert "command" not in payload["next_actions"][3]
    assert str(strategy_file) not in result.stdout


def write_minimal_strategy_file(path: Path) -> None:
    path.write_text(
        "roles:\n"
        "  - id: reviewer\n"
        "    name: Evidence Reviewer\n"
        "    archetype: inspector\n"
        "    prompt_ref: inspector.md\n"
        "steps:\n"
        "  - id: review\n"
        "    role_id: reviewer\n",
        encoding="utf-8",
    )


def write_loop_create_inputs(tmp_path: Path) -> tuple[Path, Path]:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return spec_path, workdir


def install_loop_create_service(monkeypatch, *, loop_id: str) -> dict[str, object]:
    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": loop_id, "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"loop creation without --start should not rerun: {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)
    return calls


def invoke_loop_create(spec_path: Path, workdir: Path, *extra_args: str):
    return CliRunner().invoke(
        cli.app,
        ["loops", "create", "--spec", str(spec_path), "--workdir", str(workdir), *extra_args],
    )


def option_value(tokens: list[str], option: str) -> str:
    return tokens[tokens.index(option) + 1]


def loopora_command_tokens(command: str) -> list[str]:
    tokens = shlex.split(command)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("--"):
        tokens = tokens[1:]
    return tokens


def parallel_strategy_source() -> dict:
    return {
        "version": 1,
        "roles": [
            _role("builder", "builder"),
            _role("contract_inspector", "inspector"),
            _role("evidence_inspector", "inspector"),
            _role("gatekeeper", "gatekeeper"),
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {
                "id": "contract_inspection_step",
                "role_id": "contract_inspector",
                "parallel_group": "inspection_pack",
                "inputs": {
                    "handoffs_from": ["builder_step"],
                    "evidence_query": {"archetypes": ["builder"], "limit": 8},
                    "iteration_memory": "summary_only",
                },
            },
            {
                "id": "evidence_inspection_step",
                "role_id": "evidence_inspector",
                "parallel_group": "inspection_pack",
                "inputs": {"handoffs_from": ["builder_step"]},
            },
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "inputs": {"handoffs_from": ["contract_inspection_step", "evidence_inspection_step"]},
            },
        ],
        "controls": [
            {
                "id": "stale_evidence_check",
                "when": {"signal": "no_evidence_progress", "after": "20m"},
                "call": {"role_id": "evidence_inspector"},
                "mode": "repair_guidance",
                "max_fires_per_run": 1,
            }
        ],
    }


def _role(role_id: str, archetype: str) -> dict:
    return {"id": role_id, "archetype": archetype, "prompt_ref": f"{archetype}.md"}
