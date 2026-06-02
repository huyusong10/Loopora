from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli


DELETED_RUN_COUNT = 2


def test_cli_loops_create_can_save_without_starting(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_saved", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def rerun(self, loop_id: str, *, background: bool = False):
            calls["rerun"] = (loop_id, background)
            return {"id": "run_saved", "status": "queued", "runs_dir": str(tmp_path / "runs" / "run_saved")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--name",
            "Saved Loop",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["name"] == "Saved Loop"
    assert "rerun" not in calls


def test_cli_loops_create_accepts_orchestration_id(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_saved", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--orchestration-id",
            "builtin:inspect_first",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["orchestration_id"] == "builtin:inspect_first"
    assert calls["create_loop"]["workflow"] is None


def test_cli_loops_delete_prints_json(monkeypatch) -> None:
    class FakeService:
        def delete_loop(self, loop_id: str):
            return {"id": loop_id, "deleted_runs": 2, "workdir": "/tmp/project"}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["loops", "delete", "loop_test"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["id"] == "loop_test"
    assert payload["deleted_runs"] == DELETED_RUN_COUNT
