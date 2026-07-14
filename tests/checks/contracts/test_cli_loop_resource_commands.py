from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli
from loopora.branding import APP_HOME_ENV
from loopora.run_evidence_package import RunEvidencePackage
from loopora.service_types import LooporaError, LooporaWorkdirUnavailableError
from cli_loop_resource_command_test_support import (
    DELETED_RUN_COUNT,
    RETRY_RUN_START_STATUS,
    assert_command_options,
    assert_recovery_summary_actions,
    assert_retry_cli_run_start_ready,
    fail_create_loop_service,
    loopora_command_tokens,
    make_workdir,
    option_value,
    payload_from,
    payload_json,
    run_start_failed_run,
    write_spec,
)


def test_cli_loops_create_can_save_without_starting(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    workdir = make_workdir(tmp_path)
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


def test_cli_loops_create_can_print_json(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    workdir = make_workdir(tmp_path)

    class FakeService:
        def create_loop(self, **kwargs):
            return {"id": "loop_saved", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(
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
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["status"] == "created"
    assert payload["loop"]["id"] == "loop_saved"
    assert payload["loop"]["name"] == "Saved Loop"
    assert payload["run"] is None
    assert "loop:" not in result.stdout


def test_cli_loops_create_accepts_orchestration_id(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    workdir = make_workdir(tmp_path)
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


def test_cli_loops_create_json_explains_missing_workdir_before_create(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    missing_workdir = tmp_path / "missing-project"

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("missing workdir preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(missing_workdir),
            "--name",
            "Blocked Loop",
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert not missing_workdir.exists()
    assert "Invalid value for '--workdir'" not in result.output
    payload = payload_from(result)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == "create"
    assert payload["workdir_state"]["status"] == "missing"
    assert payload["workdir_state"]["summary"] == payload["summary"]
    assert_recovery_summary_actions(
        payload, "loop_workdir_recovery_summary", "workdir_state_status", "missing", ["create_workdir", "retry_loop_create", "confirm_readiness"]
    )
    assert "mkdir -p" in payload["next_actions"][0]["command"]
    assert "loopora loops create --spec" in payload["next_actions"][1]["command"]
    assert "--json" in payload["next_actions"][1]["command"]
    assert "loopora doctor --workdir" in payload["next_actions"][2]["command"]
    assert payload["next_actions"][2]["after_action"] == "retry_loop_create"


def test_cli_loops_create_json_omits_stale_commands_when_workdir_must_be_chosen(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    original = workdir_file.read_text(encoding="utf-8")

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("file workdir preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir_file),
            "--name",
            "Blocked Loop",
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert workdir_file.read_text(encoding="utf-8") == original
    payload = payload_from(result)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["workdir_state"]["status"] == "not_directory"
    assert_recovery_summary_actions(
        payload, "loop_workdir_recovery_summary", "workdir_state_status", "not_directory", ["choose_workdir", "retry_loop_create", "confirm_readiness"]
    )
    assert "command" not in payload["next_actions"][1]
    assert "command" not in payload["next_actions"][2]
    assert payload["next_actions"][2]["after_action"] == "retry_loop_create"


def test_cli_loops_create_json_reports_required_compose_paths_without_typer_usage(monkeypatch, tmp_path: Path) -> None:
    spec_path = write_spec(tmp_path)
    workdir = make_workdir(tmp_path)

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("required path preflight must not create a loop"))
    missing_spec = CliRunner().invoke(cli.app, ["loops", "create", "--workdir", str(workdir), "--json"])
    blank_spec = CliRunner().invoke(cli.app, ["loops", "create", "--spec", "", "--workdir", str(workdir), "--json"])
    missing_workdir = CliRunner().invoke(cli.app, ["loops", "create", "--spec", str(spec_path), "--json"])
    blank_workdir = CliRunner().invoke(cli.app, ["loops", "create", "--spec", str(spec_path), "--workdir", "", "--json"])
    for result in [missing_spec, blank_spec]:
        assert result.exit_code == 1
        assert "Missing option '--spec'" not in result.output
        assert "Usage:" not in result.output
        payload = payload_from(result)
        assert payload["loop_recovery"] == "target_spec_unavailable"
        assert payload["status"] == "blocked_by_spec"
        assert payload["spec_path"] == ""
        assert payload["spec_state"]["status"] == "required"
        assert_recovery_summary_actions(
            payload, "loop_spec_recovery_summary", "spec_state_status", "required", ["create_spec", "retry_loop_create", "choose_spec"]
        )
        actions = payload["next_actions"]
        retry_tokens = loopora_command_tokens(actions[1]["command_template"])
        assert (
            "loopora spec init <spec-path>" in actions[0]["command_template"],
            "loopora loops create --spec <spec-path>" in actions[1]["command_template"],
            option_value(retry_tokens, "--workdir"),
            "command" in actions[0],
            "command" in actions[1],
        ) == (True, True, str(workdir.resolve()), False, False)
        assert str(Path.cwd()) not in result.stdout
    for result in [missing_workdir, blank_workdir]:
        assert result.exit_code == 1
        assert "Missing option '--workdir'" not in result.output
        assert "Usage:" not in result.output
        payload = payload_from(result)
        assert payload["loop_recovery"] == "target_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["workdir"] == ""
        assert payload["workdir_state"]["status"] == "required"
        assert_recovery_summary_actions(
            payload, "loop_workdir_recovery_summary", "workdir_state_status", "required", ["choose_workdir", "retry_loop_create", "confirm_readiness"]
        )
        assert "command" not in payload["next_actions"][1]
        assert "command" not in payload["next_actions"][2]
        assert payload["next_actions"][2]["after_action"] == "retry_loop_create"
        assert str(Path.cwd()) not in result.stdout


def test_cli_loops_create_explains_missing_spec_before_create(monkeypatch, tmp_path: Path) -> None:
    workdir = make_workdir(tmp_path)
    missing_spec = tmp_path / "missing-spec.md"

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("missing spec preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--name",
            "Blocked Loop",
            "--orchestration-id",
            "builtin:repair_loop",
        ],
    )

    assert result.exit_code == 1
    assert not missing_spec.exists()
    assert "Invalid value for '--spec'" not in result.output
    assert "Loopora Loop create is blocked" in result.output
    assert "spec_state: missing" in result.output
    assert "Spec file does not exist yet" in result.output
    assert f"loopora spec init {missing_spec.resolve()!s}" in result.output
    assert "--orchestration-id builtin:repair_loop" in result.output
    assert "loopora loops create --spec" in result.output


def test_cli_loops_create_json_explains_missing_spec_before_create(monkeypatch, tmp_path: Path) -> None:
    workdir = make_workdir(tmp_path)
    missing_spec = tmp_path / "missing-spec.md"
    strategy_file = tmp_path / "strategy.yml"
    strategy_file.write_text("preset: inspect_first\n", encoding="utf-8")

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("missing spec preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(missing_spec),
            "--workdir",
            str(workdir),
            "--name",
            "Blocked Loop",
            "--executor",
            "claude",
            "--model",
            "opus-test",
            "--completion-mode",
            "rounds",
            "--iteration-interval-seconds",
            "2.5",
            "--command-cli",
            "agent-cli",
            "--command-arg",
            "{prompt}",
            "--max-iters",
            "0",
            "--role-model",
            "builder=gpt-5",
            "--strategy-file",
            str(strategy_file),
            "--start",
            "--background",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert not missing_spec.exists()
    assert "Invalid value for '--spec'" not in result.output
    payload = payload_from(result)
    assert payload["loop_recovery"] == "target_spec_unavailable"
    assert payload["status"] == "blocked_by_spec"
    assert payload["action"] == "create"
    assert payload["spec_state"]["status"] == "missing"
    assert payload["spec_state"]["summary"] == payload["summary"]
    assert_recovery_summary_actions(payload, "loop_spec_recovery_summary", "spec_state_status", "missing", ["create_spec", "retry_loop_create", "choose_spec"])
    assert f"loopora spec init {missing_spec.resolve()!s}" in payload["next_actions"][0]["command"]
    init_tokens = loopora_command_tokens(payload["next_actions"][0]["command"])
    assert option_value(init_tokens, "--strategy-file") == str(strategy_file.resolve(strict=False))
    retry_tokens = loopora_command_tokens(payload["next_actions"][1]["command"])
    assert retry_tokens[:3] == ["loopora", "loops", "create"]
    assert_command_options(
        retry_tokens,
        {
            "--spec": str(missing_spec.resolve()),
            "--workdir": str(workdir.resolve()),
            "--name": "Blocked Loop",
            "--executor": "claude",
            "--model": "opus-test",
            "--completion-mode": "rounds",
            "--iteration-interval-seconds": "2.5",
            "--command-cli": "agent-cli",
            "--command-arg": "{prompt}",
            "--max-iters": "0",
            "--role-model": "builder=gpt-5",
            "--strategy-file": str(strategy_file.resolve(strict=False)),
        },
    )
    assert "--start" in retry_tokens
    assert "--background" in retry_tokens
    assert "--json" in retry_tokens
    assert "command" not in payload["next_actions"][2]


def test_cli_loops_create_json_redacts_uninspectable_spec(monkeypatch, tmp_path: Path) -> None:
    workdir = make_workdir(tmp_path)
    spec_path = tmp_path / "blocked-spec.md"
    private_path = tmp_path / "private" / "blocked-spec.md"
    blocked_resolved = spec_path.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)
    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("uninspectable spec preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = payload_from(result)
    assert payload["status"] == "blocked_by_spec"
    assert payload["spec_state"]["status"] == "unavailable"
    assert payload["spec_state"]["error"] == "spec path could not be inspected"
    assert [item["kind"] for item in payload["next_actions"]] == ["choose_spec", "retry_loop_create"]
    assert "command" not in payload["next_actions"][1]
    encoded = payload_json(payload)
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded


def test_cli_loops_create_plain_does_not_retry_directory_spec_path(monkeypatch, tmp_path: Path) -> None:
    workdir = make_workdir(tmp_path)
    spec_dir = tmp_path / "spec-as-directory.md"
    spec_dir.mkdir()

    monkeypatch.setattr(cli, "create_service", fail_create_loop_service("directory spec preflight must not create a loop"))
    result = CliRunner().invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_dir),
            "--workdir",
            str(workdir),
        ],
    )

    assert result.exit_code == 1
    assert "spec_state: not_file" in result.output
    assert "Choose an existing Markdown spec" in result.output
    assert "loopora loops create --spec" not in result.output


def test_cli_loops_rerun_explains_missing_saved_workdir(monkeypatch, tmp_path: Path) -> None:
    missing_workdir = tmp_path / "missing-project"
    app_home = tmp_path / "custom-home"
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    class FakeService:
        def rerun(self, loop_id: str, *, background: bool = False):
            assert loop_id == "loop_missing_workdir"
            assert background is False
            raise LooporaWorkdirUnavailableError(workdir=str(missing_workdir), workdir_state="missing")

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_missing_workdir"])
    assert result.exit_code == 1
    assert not missing_workdir.exists()
    assert "Loopora Loop rerun is blocked" in result.output
    assert "project directory state: missing" in result.output
    assert "note:" in result.output
    assert "summary:" not in result.output
    assert "Target project directory does not exist yet" in result.output
    assert f"{source_entry} doctor --workdir" in result.output
    assert f"{APP_HOME_ENV}={app_home!s} {source_entry} loops rerun loop_missing_workdir" in result.output


def test_cli_loops_rerun_can_print_json(monkeypatch, tmp_path: Path) -> None:
    class FakeService:
        def rerun(self, loop_id: str, *, background: bool = False):
            assert loop_id == "loop_saved"
            assert background is False
            return {"id": "run_saved", "status": "queued", "runs_dir": str(tmp_path / "runs" / "run_saved")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_saved", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["id"] == "run_saved"
    assert payload["status"] == "queued"
    assert "run:" not in result.stdout


def test_cli_loops_rerun_json_projects_lifecycle_failure_recovery(monkeypatch) -> None:
    class FakeService:
        def rerun(self, loop_id: str, *, background: bool = False):
            assert loop_id == "loop_saved"
            assert background is False
            return run_start_failed_run(loop_id)

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_saved", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["id"] == "run_failed_start"
    assert payload["status"] == "failed"
    assert payload["status_label"] == "run_start_failed"
    assert payload["run_recovery"] == "retry_run_start"
    assert payload["task_verdict"]["status"] == "not_evaluated"
    action = payload["next_actions"][0]
    assert action["kind"] == "retry_run_start"
    assert loopora_command_tokens(action["command"]) == ["loopora", "loops", "rerun", "loop_saved", "--json"]


def test_cli_loops_rerun_json_explains_missing_saved_workdir(monkeypatch, tmp_path: Path) -> None:
    missing_workdir = tmp_path / "missing-project"
    app_home = tmp_path / "custom-home"
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    class FakeService:
        def start_next_run(self, _loop_id: str):
            raise LooporaWorkdirUnavailableError(workdir=str(missing_workdir), workdir_state="missing")

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(
        cli.app,
        ["loops", "rerun", "loop_missing_workdir", "--background", "--json"],
    )
    assert result.exit_code == 1
    assert not missing_workdir.exists()
    payload = payload_from(result)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == "rerun"
    assert payload["workdir_state"]["status"] == "missing"
    retry_tokens = loopora_command_tokens(payload["next_actions"][2]["command"])
    assert retry_tokens == ["loopora", "loops", "rerun", "loop_missing_workdir", "--background", "--json"]


def test_cli_loops_rerun_json_requires_blank_saved_workdir_without_current_directory(monkeypatch) -> None:
    class FakeService:
        def rerun(self, loop_id: str, *, background: bool = False):
            assert loop_id == "loop_blank_workdir"
            assert background is False
            raise LooporaWorkdirUnavailableError(workdir="", workdir_state="required")

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_blank_workdir", "--json"])
    assert result.exit_code == 1
    payload = payload_from(result)
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["action"] == "rerun"
    assert payload["workdir"] == ""
    assert payload["workdir_state"]["status"] == "required"
    assert payload["workdir_state"]["error"] == "workdir is required"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "choose_workdir",
        "confirm_readiness",
        "retry_loop_rerun",
    ]
    assert all("command" not in item for item in payload["next_actions"])
    assert str(Path.cwd()) not in result.stdout


def test_cli_loops_list_can_print_json(monkeypatch, tmp_path: Path) -> None:
    class FakeService:
        def list_loops(self):
            return [
                {
                    "id": "loop_saved",
                    "name": "Saved Loop",
                    "workdir": str(tmp_path / "project"),
                    "latest_status": "queued",
                    "executor_kind": "codex",
                    "model": "",
                }
            ]

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "list", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["status"] == "ok"
    assert payload["count"] == 1
    assert payload["loops"][0]["id"] == "loop_saved"


def test_cli_loops_list_surfaces_lifecycle_failure_as_retry_not_plain_failed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    class FakeService:
        def list_loops(self):
            failure = run_start_failed_run("loop_failed_start")
            return [
                {
                    "id": "loop_failed_start",
                    "name": "Failed Start Loop",
                    "workdir": str(tmp_path / "project"),
                    "latest_status": "failed",
                    "latest_error_message": failure["error_message"],
                    "latest_task_verdict_json": failure["task_verdict"],
                    "model": "",
                }
            ]

    monkeypatch.setattr(cli, "create_service", FakeService)
    plain = CliRunner().invoke(cli.app, ["loops", "list"])
    json_result = CliRunner().invoke(cli.app, ["loops", "list", "--json"])
    assert plain.exit_code == 0, plain.stdout
    assert "[run_start_failed]" in plain.stdout
    assert "[failed]" not in plain.stdout
    assert json_result.exit_code == 0, json_result.stdout
    payload = payload_from(json_result)
    listed = payload["loops"][0]
    assert (listed["latest_status"], listed["latest_status_label"], listed["latest_run_recovery"]) == RETRY_RUN_START_STATUS
    action = assert_retry_cli_run_start_ready(listed)
    assert f"{source_entry} loops rerun loop_failed_start" in action["command"]


def test_cli_loops_list_json_errors_are_structured(monkeypatch) -> None:
    class FailingService:
        def list_loops(self):
            raise LooporaError("loop list unavailable")

    monkeypatch.setattr(cli, "create_service", FailingService)
    result = CliRunner().invoke(cli.app, ["loops", "list", "--json"])
    expected = {"status": "error", "error": "loop list unavailable"}
    assert (result.exit_code, payload_from(result), result.stderr) == (1, expected, "")


def test_cli_loop_status_projects_latest_lifecycle_failure_recovery(monkeypatch) -> None:
    class FakeService:
        def get_status(self, identifier: str):
            assert identifier == "loop_failed_start"
            return (
                "loop",
                {
                    "id": "loop_failed_start",
                    "runs": [run_start_failed_run("loop_failed_start")],
                },
            )

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "status", "loop_failed_start"])
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["latest_run_id"] == "run_failed_start"
    assert (payload["latest_status"], payload["latest_status_label"], payload["latest_run_recovery"]) == RETRY_RUN_START_STATUS
    action = assert_retry_cli_run_start_ready(payload)
    assert loopora_command_tokens(action["command"]) == ["loopora", "loops", "rerun", "loop_failed_start"]


def test_cli_run_status_projects_lifecycle_failure_recovery(monkeypatch) -> None:
    class FakeService:
        def get_status(self, identifier: str):
            assert identifier == "run_failed_start"
            return ("run", run_start_failed_run("loop_failed_start"))

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = CliRunner().invoke(cli.app, ["loops", "status", "run_failed_start"])
    assert result.exit_code == 0, result.stdout
    payload = payload_from(result)
    assert payload["status"] == "failed"
    assert (payload["status_label"], payload["run_recovery"]) == ("run_start_failed", "retry_run_start")
    action = assert_retry_cli_run_start_ready(payload)
    assert loopora_command_tokens(action["command"]) == ["loopora", "loops", "rerun", "loop_failed_start"]


def test_cli_loops_stop_rerun_delete_help_keeps_lifecycle_boundaries(monkeypatch) -> None:
    runner = CliRunner()
    help_text = {}
    for name in ("stop", "rerun", "delete"):
        result = runner.invoke(cli.app, ["loops", name, "--help"])
        assert result.exit_code == 0, result.stdout
        help_text[name] = " ".join(result.stdout.split())
    assert "Stop is a lifecycle request for an existing Run" in help_text["stop"]
    assert "it is not task proof and does not delete Loop artifacts" in help_text["stop"]
    assert "Rerun starts the next Run from a saved reviewed Loop definition" in help_text["rerun"]
    assert all(
        term in help_text["rerun"] for term in ("does not rewrite the Loop definition", "replace earlier run history", "resume an exact same-Agent session")
    )
    assert all(
        term in help_text["delete"]
        for term in ("Delete removes one saved Loop definition", "does not delete the target project workdir", "--dry-run to preview the delete scope")
    )

    class FakeService:
        def stop_run(self, run_id: str):
            return {"id": run_id, "loop_id": "loop_saved", "status": "stopped"}

    monkeypatch.setattr(cli, "create_service", FakeService)
    result = runner.invoke(cli.app, ["loops", "stop", "run_active", "--json"])
    assert result.exit_code == 0, result.stdout
    assert payload_from(result)["status"] == "stopped"
    assert "stop requested" not in result.stdout


def test_cli_loops_export_run_requires_explicit_overwrite_and_reports_private_scope(monkeypatch, tmp_path: Path) -> None:
    package = RunEvidencePackage(
        filename="loopora-evidence-run_saved.zip",
        content=b"review package",
        manifest={"content_scope": "private_task_review", "files": [{"path": "summary.md"}]},
    )

    class FakeService:
        def build_run_evidence_package(self, run_id: str):
            assert run_id == "run_saved"
            return package

    monkeypatch.setattr(cli, "create_service", FakeService)
    output = tmp_path / "evidence.zip"
    output.write_bytes(b"existing")
    runner = CliRunner()

    refused = runner.invoke(cli.app, ["loops", "export-run", "run_saved", "--output", str(output)])
    assert output.read_bytes() == b"existing"
    exported = runner.invoke(cli.app, ["loops", "export-run", "run_saved", "--output", str(output), "--force", "--json"])

    assert refused.exit_code == 1
    assert "pass --force to replace it" in refused.output
    assert output.read_bytes() == b"review package"
    payload = payload_from(exported)
    assert payload == {
        "status": "exported",
        "run_id": "run_saved",
        "path": str(output.resolve()),
        "public_safe": False,
        "content_scope": "private_task_review",
        "included_file_count": 1,
    }


def test_cli_loops_delete_dry_run_previews_scope_without_deleting(monkeypatch) -> None:
    calls: list[str] = []

    class FakeService:
        def preview_loop_delete(self, loop_id: str):
            calls.append("preview_loop_delete")
            return {
                "status": "dry_run",
                "dry_run": True,
                "delete_allowed": True,
                "would_delete": {"loop": loop_id, "run_count": DELETED_RUN_COUNT, "run_ids": ["run_one", "run_two"]},
                "blocked_by_active_runs": [],
                "does_not_delete": ["target_project_workdir", "source_spec_file", "exported_plan_files", "external_provider_history"],
            }

        def delete_loop(self, loop_id: str):
            calls.append("delete_loop")
            return {"id": loop_id, "deleted_runs": DELETED_RUN_COUNT, "workdir": "/tmp/project"}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()
    preview = runner.invoke(cli.app, ["loops", "delete", "loop_test", "--dry-run"])
    result = runner.invoke(cli.app, ["loops", "delete", "loop_test"])
    assert preview.exit_code == result.exit_code == 0
    preview_payload = payload_from(preview)
    assert preview_payload["status"] == "dry_run"
    assert preview_payload["delete_allowed"] is True
    assert preview_payload["would_delete"] == {"loop": "loop_test", "run_count": DELETED_RUN_COUNT, "run_ids": ["run_one", "run_two"]}
    assert preview_payload["does_not_delete"] == ["target_project_workdir", "source_spec_file", "exported_plan_files", "external_provider_history"]
    assert preview_payload["next_action_kinds"] == preview_payload["next_action_ready_now_kinds"] == ["delete_loop"]
    assert "loopora loops delete loop_test" in preview_payload["next_actions"][0]["command"]
    assert payload_from(result)["deleted_runs"] == DELETED_RUN_COUNT
    assert calls == ["preview_loop_delete", "delete_loop"]


def test_cli_loop_status_and_delete_json_errors_are_structured(monkeypatch) -> None:
    class FailingService:
        def get_status(self, _identifier: str):
            raise LooporaError("loop status unavailable")

        def delete_loop(self, _loop_id: str):
            raise LooporaError("loop delete unavailable")

    monkeypatch.setattr(cli, "create_service", FailingService)
    runner = CliRunner()
    status = runner.invoke(cli.app, ["loops", "status", "loop_missing"])
    delete = runner.invoke(cli.app, ["loops", "delete", "loop_missing"])
    assert status.exit_code == delete.exit_code == 1
    assert payload_from(status) == {"status": "error", "error": "loop status unavailable"}
    assert payload_from(delete) == {"status": "error", "error": "loop delete unavailable"}
    assert status.stderr == delete.stderr == ""
