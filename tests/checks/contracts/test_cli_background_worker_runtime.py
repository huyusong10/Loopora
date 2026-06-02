from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import cli


def test_cli_run_supports_command_mode_background_and_role_models(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_cmd", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def start_run(self, loop_id: str):
            calls["start_run"] = loop_id
            return {
                "id": "run_cmd",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_cmd"),
                "workdir": str(workdir),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned_run_id"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--executor",
            "codex",
            "--executor-mode",
            "command",
            "--command-cli",
            "codex",
            "--command-arg",
            "exec",
            "--command-arg",
            "--json",
            "--command-arg",
            "--output-schema",
            "--command-arg",
            "{schema_path}",
            "--command-arg",
            "--output-last-message",
            "--command-arg",
            "{output_path}",
            "--command-arg",
            "--model",
            "--command-arg",
            "{model}",
            "--command-arg",
            "{prompt}",
            "--model",
            "gpt-5.4-mini",
            "--role-model",
            "generator=gpt-5.4",
            "--role-model",
            "verifier=gpt-5.4-mini",
            "--background",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["start_run"] == "loop_cmd"
    assert calls["spawned_run_id"] == "run_cmd"
    assert calls["create_loop"]["executor_mode"] == "command"
    assert calls["create_loop"]["command_cli"] == "codex"
    assert "{schema_path}" in calls["create_loop"]["command_args_text"]
    assert "{model}" in calls["create_loop"]["command_args_text"]
    assert calls["create_loop"]["role_models"] == {
        "builder": "gpt-5.4",
        "gatekeeper": "gpt-5.4-mini",
    }


def test_cli_loops_rerun_background_spawns_worker(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class FakeService:
        def start_run(self, loop_id: str):
            calls["start_run"] = loop_id
            return {
                "id": "run_background",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_background"),
                "workdir": str(tmp_path / "workdir"),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["loops", "rerun", "loop_saved", "--background"])

    assert result.exit_code == 0, result.stdout
    assert calls["start_run"] == "loop_saved"
    assert calls["spawned"] == "run_background"
