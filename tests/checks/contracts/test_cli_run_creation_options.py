from __future__ import annotations

import json
from pathlib import Path
import shlex

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli
from loopora.service_types import LooporaWorkdirUnavailableError


ROUND_MODE_ITERATION_INTERVAL_SECONDS = 60.0


def test_cli_loops_help_keeps_saved_loop_library_behind_review() -> None:
    runner = CliRunner()
    normalized = {}
    for name, args in (("group", ["loops", "--help"]), ("create", ["loops", "create", "--help"]), ("list", ["loops", "list", "--help"]), ("status", ["loops", "status", "--help"]), ("rerun", ["loops", "rerun", "--help"])):
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 0, result.stdout
        normalized[name] = " ".join(result.stdout.split())
    normalized_group = normalized["group"]
    for term in ("Saved Loops are the library and operations surface after a Loop has been reviewed", "For a new task, leave this group", "loopora start", "loopora fit", 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742', "same-Agent project entry matching your current host", 'loopora init <agent> --workdir "$PWD"', 'loopora doctor --workdir "$PWD"'):
        assert term in normalized_group
    assert normalized_group.index("Fit Guide/Web choices path") < normalized_group.index("same-Agent path")
    assert normalized_group.index("same-Agent path") < normalized_group.index("/loopora-plan") < normalized_group.index("/loopora-run")
    assert "loops list/status/rerun" in normalized_group
    assert all(term in normalized_group for term in ("evidence", "verdict", "residual risk", "next action", "retry-start state"))
    assert all(term in normalized["create"] for term in ("Expert saved-Loop creation path", "reviewed Markdown spec", "existing target workdir"))
    assert all(term in normalized["create"] for term in ("Without `--start`", "with `--start`", "`--background` queues"))
    assert (all(term in normalized["create"] for term in ("For first use, leave this direct-create command", "loopora start", "loopora fit", "Fit Guide/Web choices path", "continue in Web after READY review", "Same-Agent path: choose the same-Agent project entry matching your current host", 'loopora init <agent> --workdir "$PWD"', 'loopora doctor --workdir "$PWD"')), normalized["create"].index("Fit Guide/Web choices path") < normalized["create"].index("Same-Agent path") < normalized["create"].index("/loopora-plan") < normalized["create"].index("/loopora-run")) == (True, True)
    for term in ("scan surface for existing work", "latest status", "first copyable next command", "loops status", "--json"):
        assert term in normalized["list"]
    for term in ("inspection surface before continuing existing work", "always prints structured JSON", "task-verdict projection", "next actions", "does not start, stop, delete, or rewrite work"):
        assert term in normalized["status"]
    for term in (
        "starts the next Run from a saved reviewed Loop",
        "seeds the next Run with its evidence gaps",
        "a recorded result stays closed",
        "does not rewrite the Loop definition",
        "resume an exact same-Agent session",
        "use `/loopora-run` to resume",
    ):
        assert term in normalized["rerun"]


def test_cli_run_help_keeps_expert_direct_path_behind_reviewed_first_use() -> None:
    result = CliRunner().invoke(cli.app, ["run", "--help"])
    normalized = " ".join(result.stdout.split())
    assert result.exit_code == 0, result.stdout
    assert all(
        term in normalized
        for term in (
            "Expert direct-run path",
            "reviewed Markdown spec",
            "existing target workdir",
            "For first use, leave this direct-run command",
            "loopora start",
            "Fit Guide/Web choices path",
            "Same-Agent path: choose the same-Agent project entry matching your current host",
            "loopora fit",
            "preview before creating or running",
            "continue in Web after READY review",
            'loopora init <agent> --workdir "$PWD"',
            'loopora doctor --workdir "$PWD"',
            'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742',
            "`--json` is for automation",
            "`--background` returns after queuing",
            "retry-start recovery",
        )
    )
    assert normalized.index("Fit Guide/Web choices path") < normalized.index("Same-Agent path")
    assert normalized.index("/loopora-plan") < normalized.index("/loopora-run")


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


def test_cli_run_can_print_json(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FakeService:
        def create_loop(self, **_kwargs):
            return {"id": "loop_test", "name": "Loop JSON", "workdir": str(workdir)}

        def rerun(self, loop_id: str, *, background: bool = False):
            assert loop_id == "loop_test"
            assert background is False
            return {"id": "run_test", "status": "running", "runs_dir": str(tmp_path / "runs" / "run_test")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "started"
    assert payload["loop"]["id"] == "loop_test"
    assert payload["run"]["id"] == "run_test"
    assert "run:" not in result.stdout


def test_cli_run_expands_home_spec_and_workdir_before_service(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    spec_path = home_dir / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = home_dir / "project"
    workdir.mkdir()
    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_home", "name": "Home Loop", "workdir": str(kwargs["workdir"])}

        def rerun(self, loop_id: str, *, background: bool = False):
            calls["rerun"] = loop_id
            calls["background"] = background
            return {"id": "run_home", "status": "running", "runs_dir": str(tmp_path / "runs" / "run_home")}

    monkeypatch.setattr(cli, "create_service", FakeService)

    result = CliRunner().invoke(cli.app, ["run", "--spec", "~/spec.md", "--workdir", "~/project"])

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["spec_path"] == spec_path.resolve()
    assert calls["create_loop"]["workdir"] == workdir.resolve()
    assert calls["rerun"] == "loop_home"


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


def test_cli_run_json_explains_missing_workdir_before_create(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    missing_workdir = tmp_path / "missing-project"

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("missing workdir preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"missing workdir preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(missing_workdir),
            "--executor-mode",
            "command",
            "--reasoning-effort",
            "high",
            "--command-cli",
            "custom-agent",
            "--command-arg",
            "{schema_path}",
            "--command-arg",
            "{output_path}",
            "--command-arg",
            "{prompt}",
            "--max-role-retries",
            "4",
            "--delta-threshold",
            "0.01",
            "--trigger-window",
            "5",
            "--regression-window",
            "3",
            "--background",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert not missing_workdir.exists()
    assert "Invalid value for '--workdir'" not in result.output
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == "run"
    assert payload["workdir_state"]["status"] == "missing"
    assert ([item["kind"] for item in payload["next_actions"]], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (["create_workdir", "retry_loop_run", "confirm_readiness"], ["create_workdir"], {"retry_loop_run": "create_workdir", "confirm_readiness": "retry_loop_run"})
    retry_tokens = _loopora_command_tokens(payload["next_actions"][1]["command"])
    assert retry_tokens[:2] == ["loopora", "run"]
    assert _option_value(retry_tokens, "--spec") == str(spec_path.resolve())
    assert _option_value(retry_tokens, "--workdir") == str(missing_workdir.resolve(strict=False))
    assert _option_value(retry_tokens, "--executor-mode") == "command"
    assert _option_value(retry_tokens, "--reasoning-effort") == "high"
    assert _option_value(retry_tokens, "--command-cli") == "custom-agent"
    assert _option_value(retry_tokens, "--command-arg") == "{schema_path}"
    assert "{output_path}" in retry_tokens
    assert "{prompt}" in retry_tokens
    assert _option_value(retry_tokens, "--max-role-retries") == "4"
    assert _option_value(retry_tokens, "--delta-threshold") == "0.01"
    assert _option_value(retry_tokens, "--trigger-window") == "5"
    assert _option_value(retry_tokens, "--regression-window") == "3"
    assert "--start" not in retry_tokens
    assert "--background" in retry_tokens
    assert "--json" in retry_tokens
    assert "loopora doctor --workdir" in payload["next_actions"][2]["command"]
    assert payload["next_actions"][2]["after_action"] == "retry_loop_run"


def test_cli_run_json_reports_required_compose_paths_without_typer_usage(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("required path preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"required path preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    missing_spec = CliRunner().invoke(cli.app, ["run", "--workdir", str(workdir), "--json"])
    blank_spec = CliRunner().invoke(cli.app, ["run", "--spec", "", "--workdir", str(workdir), "--json"])
    missing_workdir = CliRunner().invoke(cli.app, ["run", "--spec", str(spec_path), "--json"])
    blank_workdir = CliRunner().invoke(cli.app, ["run", "--spec", str(spec_path), "--workdir", "", "--json"])

    for result in [missing_spec, blank_spec]:
        assert result.exit_code == 1
        assert "Missing option '--spec'" not in result.output
        assert "Usage:" not in result.output
        payload = json.loads(result.stdout)
        assert payload["loop_recovery"] == "target_spec_unavailable"
        assert payload["status"] == "blocked_by_spec"
        assert payload["spec_path"] == ""
        assert payload["spec_state"]["status"] == "required"
        actions = payload["next_actions"]
        retry_tokens = _loopora_command_tokens(actions[1]["command_template"])
        assert ([item["kind"] for item in actions], "loopora spec init <spec-path>" in actions[0]["command_template"], "loopora run --spec <spec-path>" in actions[1]["command_template"], _option_value(retry_tokens, "--workdir"), "command" in actions[0], "command" in actions[1]) == (["create_spec", "retry_loop_run", "choose_spec"], True, True, str(workdir.resolve()), False, False)
        assert str(Path.cwd()) not in result.stdout

    for result in [missing_workdir, blank_workdir]:
        assert result.exit_code == 1
        assert "Missing option '--workdir'" not in result.output
        assert "Usage:" not in result.output
        payload = json.loads(result.stdout)
        assert payload["loop_recovery"] == "target_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["workdir"] == ""
        assert payload["workdir_state"]["status"] == "required"
        assert ([item["kind"] for item in payload["next_actions"]], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (["choose_workdir", "retry_loop_run", "confirm_readiness"], ["choose_workdir"], {"retry_loop_run": "choose_workdir", "confirm_readiness": "retry_loop_run"})
        assert "command" not in payload["next_actions"][1]
        assert "command" not in payload["next_actions"][2]
        assert payload["next_actions"][2]["after_action"] == "retry_loop_run"
        assert str(Path.cwd()) not in result.stdout


def test_cli_run_json_projects_invalid_path_probe_as_unavailable(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("invalid path preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"invalid path preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    invalid_workdir = CliRunner().invoke(
        cli.app,
        ["run", "--spec", str(spec_path), "--workdir", "bad\0workdir", "--json"],
    )
    invalid_spec = CliRunner().invoke(
        cli.app,
        ["run", "--spec", "bad\0spec.md", "--workdir", str(workdir), "--json"],
    )

    assert invalid_workdir.exit_code == 1
    assert "Usage:" not in invalid_workdir.output
    workdir_payload = json.loads(invalid_workdir.stdout)
    assert workdir_payload["loop_recovery"] == "target_workdir_unavailable"
    assert workdir_payload["status"] == "blocked_by_workdir"
    assert workdir_payload["workdir"] == ""
    assert workdir_payload["workdir_state"]["status"] == "unavailable"
    assert ([item["kind"] for item in workdir_payload["next_actions"]], workdir_payload["next_action_ready_now_kinds"], workdir_payload["next_action_ready_after_actions"]) == (["choose_workdir", "retry_loop_run", "confirm_readiness"], ["choose_workdir"], {"retry_loop_run": "choose_workdir", "confirm_readiness": "retry_loop_run"})
    assert all("command" not in item for item in workdir_payload["next_actions"])
    assert "embedded null" not in invalid_workdir.output
    assert str(Path.cwd()) not in invalid_workdir.output

    assert invalid_spec.exit_code == 1
    assert "Usage:" not in invalid_spec.output
    spec_payload = json.loads(invalid_spec.stdout)
    assert spec_payload["loop_recovery"] == "target_spec_unavailable"
    assert spec_payload["status"] == "blocked_by_spec"
    assert spec_payload["spec_path"] == ""
    assert spec_payload["spec_state"]["status"] == "unavailable"
    assert [item["kind"] for item in spec_payload["next_actions"]] == ["choose_spec", "retry_loop_run"]
    assert all("command" not in item for item in spec_payload["next_actions"])
    assert "embedded null" not in invalid_spec.output
    assert str(Path.cwd()) not in invalid_spec.output


def test_cli_run_projects_service_workdir_race_as_compose_recovery(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    racing_workdir = tmp_path / "racing-workdir"
    racing_workdir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            racing_workdir.rmdir()
            raise LooporaWorkdirUnavailableError(workdir=str(racing_workdir), workdir_state="missing", action="compose")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        ["run", "--spec", str(spec_path), "--workdir", str(racing_workdir), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == "run"
    assert payload["workdir_state"]["status"] == "missing"
    assert ([item["kind"] for item in payload["next_actions"]], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (["create_workdir", "retry_loop_run", "confirm_readiness"], ["create_workdir"], {"retry_loop_run": "create_workdir", "confirm_readiness": "retry_loop_run"})
    assert payload["next_actions"][2]["after_action"] == "retry_loop_run"
    assert not racing_workdir.exists()


def test_cli_run_explains_missing_spec_before_create(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    missing_spec = tmp_path / "missing-spec.md"
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("missing spec preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"missing spec preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
        ],
    )

    assert result.exit_code == 1
    assert not missing_spec.exists()
    assert "Invalid value for '--spec'" not in result.output
    assert "Loopora Loop run is blocked" in result.output
    assert "spec_state: missing" in result.output
    assert "note:" in result.output
    assert "summary:" not in result.output
    assert "Spec file does not exist yet" in result.output
    assert f"{source_entry} spec init {missing_spec.resolve()!s}" in result.output
    assert f"{source_entry} run --spec" in result.output
    assert f"loopora spec init {missing_spec.resolve()!s}" in result.output
    assert "loopora run --spec" in result.output


def test_cli_run_json_explains_missing_spec_before_create(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    missing_spec = tmp_path / "missing-spec.md"

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("missing spec preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"missing spec preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert not missing_spec.exists()
    assert "Invalid value for '--spec'" not in result.output
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "target_spec_unavailable"
    assert payload["status"] == "blocked_by_spec"
    assert payload["action"] == "run"
    assert payload["spec_state"]["status"] == "missing"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "create_spec",
        "retry_loop_run",
        "choose_spec",
    ]
    assert f"loopora spec init {missing_spec.resolve()!s}" in payload["next_actions"][0]["command"]
    init_tokens = _loopora_command_tokens(payload["next_actions"][0]["command"])
    assert _option_value(init_tokens, "--strategy-preset") == "quality_gate"
    assert "loopora run --spec" in payload["next_actions"][1]["command"]
    assert "--json" in payload["next_actions"][1]["command"]
    assert "command" not in payload["next_actions"][2]


def test_cli_run_json_does_not_retry_directory_spec_path(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    spec_dir = tmp_path / "spec-as-directory.md"
    spec_dir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("directory spec preflight must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"directory spec preflight must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_dir),
            "--workdir",
            str(workdir),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "target_spec_unavailable"
    assert payload["status"] == "blocked_by_spec"
    assert payload["action"] == "run"
    assert payload["spec_state"]["status"] == "not_file"
    assert [item["kind"] for item in payload["next_actions"]] == ["choose_spec", "retry_loop_run"]
    assert "command" not in payload["next_actions"][1]


def test_cli_loop_compose_numeric_option_errors_are_structured_before_preflight(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("invalid compose options must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"invalid compose options must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    runner = CliRunner()
    json_cases = [
        (
            ["run", "--spec", str(spec_path), "--workdir", str(workdir), "--max-iters", "-1", "--json"],
            {"status": "error", "error": "invalid --max-iters: must be >= 0"},
        ),
        (
            [
                "loops",
                "create",
                "--spec",
                str(spec_path),
                "--workdir",
                str(workdir),
                "--trigger-window",
                "0",
                "--json",
            ],
            {"status": "error", "error": "invalid --trigger-window: must be >= 1"},
        ),
        (
            [
                "run",
                "--spec",
                str(spec_path),
                "--workdir",
                str(workdir),
                "--iteration-interval-seconds",
                "nope",
                "--json",
            ],
            {"status": "error", "error": "invalid --iteration-interval-seconds: must be a finite number"},
        ),
        (
            [
                "loops",
                "create",
                "--spec",
                str(spec_path),
                "--workdir",
                str(workdir),
                "--delta-threshold",
                "nan",
                "--json",
            ],
            {"status": "error", "error": "invalid --delta-threshold: must be a finite number"},
        ),
    ]

    for args, expected in json_cases:
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 1
        assert json.loads(result.stdout) == expected
        assert result.stderr == ""
        assert "Usage:" not in result.output
        assert "Invalid value" not in result.output
        assert "loop_recovery" not in result.output

    plain = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--regression-window",
            "0",
        ],
    )

    assert plain.exit_code == 2
    assert plain.stdout == ""
    assert "invalid --regression-window: must be >= 1" in plain.stderr
    assert "Usage:" not in plain.output
    assert "Invalid value" not in plain.output


def test_cli_loop_compose_semantic_option_errors_are_structured_before_preflight(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    missing_spec = tmp_path / "missing-spec.md"
    missing_workdir = tmp_path / "missing-project"
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FailService:
        def create_loop(self, **_kwargs):
            raise AssertionError("invalid compose options must not create a loop")

        def rerun(self, _loop_id: str, *, background: bool = False):
            raise AssertionError(f"invalid compose options must not start a run: background={background}")

    monkeypatch.setattr(cli, "create_service", FailService)
    runner = CliRunner()
    exact_cases = [
        (
            ["run", "--spec", str(spec_path), "--workdir", str(missing_workdir), "--executor", "bogus", "--json"],
            "invalid --executor: unsupported executor kind: 'bogus'. Expected one of: codex, claude, opencode, custom",
        ),
        (
            [
                "loops",
                "create",
                "--spec",
                str(missing_spec),
                "--workdir",
                str(workdir),
                "--executor-mode",
                "banana",
                "--json",
            ],
            "invalid --executor-mode: unsupported executor mode: 'banana'. Expected one of: preset, command",
        ),
        (
            [
                "run",
                "--spec",
                str(missing_spec),
                "--workdir",
                str(workdir),
                "--completion-mode",
                "banana",
                "--json",
            ],
            "invalid --completion-mode: unsupported completion mode: banana",
        ),
        (
            [
                "loops",
                "create",
                "--spec",
                str(missing_spec),
                "--workdir",
                str(workdir),
                "--role-model",
                "badvalue",
                "--json",
            ],
            "invalid --role-model: expected ROLE=MODEL",
        ),
    ]

    for args, expected_error in exact_cases:
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 1
        assert json.loads(result.stdout) == {"status": "error", "error": expected_error}
        assert result.stderr == ""
        assert "Usage:" not in result.output
        assert "Invalid value" not in result.output
        assert "loop_recovery" not in result.output

    command_arg = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--executor-mode",
            "command",
            "--command-arg",
            "{schema_path}",
            "--json",
        ],
    )
    assert command_arg.exit_code == 1
    command_arg_payload = json.loads(command_arg.stdout)
    assert command_arg_payload["status"] == "error"
    assert command_arg_payload["error"].startswith(
        "invalid --command-arg: custom command is missing required placeholders:"
    )
    assert "{prompt}" in command_arg_payload["error"]
    assert "{output_path}" in command_arg_payload["error"]
    assert "loop_recovery" not in command_arg.output

    preset = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--strategy-preset",
            "unknown-preset",
            "--json",
        ],
    )
    assert preset.exit_code == 1
    preset_payload = json.loads(preset.stdout)
    assert preset_payload["status"] == "error"
    assert preset_payload["error"].startswith("invalid --strategy-preset: unknown workflow preset: unknown-preset")
    assert "Expected one of:" in preset_payload["error"]
    assert "loop_recovery" not in preset.output

    plain = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(missing_workdir),
            "--executor",
            "custom",
        ],
    )

    assert plain.exit_code == 2
    assert plain.stdout == ""
    assert "invalid --executor-mode: Custom Command only supports command mode" in plain.stderr
    assert "Usage:" not in plain.output
    assert "Invalid value" not in plain.output


def _option_value(tokens: list[str], option: str) -> str:
    return tokens[tokens.index(option) + 1]

def _loopora_command_tokens(command: str) -> list[str]:
    tokens = shlex.split(command)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("--"):
        tokens = tokens[1:]
    return tokens
