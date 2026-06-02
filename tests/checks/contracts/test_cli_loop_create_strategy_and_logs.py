from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from loopora import cli
from db_test_support import _read_service_log_records


def test_cli_loop_creation_emits_structured_logs(monkeypatch, tmp_path: Path) -> None:
    spec_path, workdir = write_loop_create_inputs(tmp_path)
    install_loop_create_service(monkeypatch, loop_id="loop_logged")

    result = invoke_loop_create(spec_path, workdir, "--name", "Logged Loop")

    assert result.exit_code == 0, result.stdout
    records = _read_service_log_records()
    created_record = next(item for item in records if item["event"] == "cli.loop.create.completed")
    assert created_record["loop_id"] == "loop_logged"
    assert created_record["context"]["start"] is False


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
