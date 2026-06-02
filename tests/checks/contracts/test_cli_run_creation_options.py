from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli


ROUND_MODE_ITERATION_INTERVAL_SECONDS = 60.0


def test_cli_run_allows_zero_max_iters(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_test"}

        def rerun(self, loop_id: str, *, background: bool = False):
            calls["rerun"] = loop_id
            calls["background"] = background
            return {"id": "run_test", "status": "running", "runs_dir": str(tmp_path / "runs" / "run_test")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--max-iters",
            "0",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["max_iters"] == 0
    assert calls["rerun"] == "loop_test"
    assert calls["background"] is False


def test_cli_run_supports_round_completion_and_iteration_interval(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_rounds"}

        def rerun(self, loop_id: str, *, background: bool = False):
            assert background is False
            calls["rerun"] = loop_id
            return {"id": "run_rounds", "status": "succeeded", "runs_dir": str(tmp_path / "runs" / "run_rounds")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--completion-mode",
            "rounds",
            "--iteration-interval-seconds",
            "60",
            "--max-iters",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["completion_mode"] == "rounds"
    assert calls["create_loop"]["iteration_interval_seconds"] == ROUND_MODE_ITERATION_INTERVAL_SECONDS
    assert calls["rerun"] == "loop_rounds"
