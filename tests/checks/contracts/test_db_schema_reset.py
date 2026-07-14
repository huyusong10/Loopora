from __future__ import annotations

import json
import shlex
import socket
import sqlite3
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

import loopora.db as db_module
from loopora import agent_adapter_command_prefix, app_state_readiness, cli
from loopora.branding import APP_HOME_ENV
from loopora.cli_common import handle_error
from loopora.db import LooporaRepository
from loopora.db_schema import CURRENT_SCHEMA_VERSION
from loopora.service import LOCAL_APP_STATE_OPEN_ERROR, create_service
from loopora.service_types import LooporaConflictError, LooporaError

from app_state_recovery_test_support import (
    APP_STATE_NOT_READY_BLOCKER,
    assert_doctor_plain_gates_web_start_before_adapter_install,
    assert_doctor_public_gates_web_start_before_adapter_install,
    assert_doctor_reports_legacy_app_state_before_adapter_install,
    assert_doctor_strict_mode_fails_ready_with_app_warning,
    assert_local_app_state_open_failure_text,
    create_legacy_app_db,
    free_local_port,
)
from db_test_support import _create_run


ROOT = Path(__file__).resolve().parents[3]


def _mkdirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir()


def _schema_user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def test_repository_initializes_schema_user_version(tmp_path: Path) -> None:
    target = tmp_path / "app.db"

    LooporaRepository(target)
    LooporaRepository(target)

    assert _schema_user_version(target) == CURRENT_SCHEMA_VERSION


def test_local_asset_root_registry_requires_absolute_paths_for_reusable_identity(
    tmp_path: Path,
) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    asset_dir = tmp_path / "asset-root"
    asset_dir.mkdir()

    row = repository.upsert_local_asset_root(
        resource_type="run",
        resource_id="run_absolute",
        path=asset_dir,
        workdir=str(tmp_path),
    )
    marked_count = repository.mark_local_asset_root_state_by_path(path=asset_dir, state="cleaned")
    updated = repository.list_local_asset_roots(resource_type="run")[0]

    assert row["path"] == str(asset_dir.absolute())
    assert marked_count == 1
    assert updated["path"] == str(asset_dir.absolute())
    assert updated["state"] == "cleaned"

    with pytest.raises(ValueError, match="local asset path must be absolute"):
        repository.upsert_local_asset_root(resource_type="run", resource_id="run_relative", path="relative-asset")
    with pytest.raises(ValueError, match="local asset path must be absolute"):
        repository.mark_local_asset_root_state_by_path(path="relative-asset", state="cleaned")


def test_local_asset_root_registry_internal_writers_use_absolute_asset_roots(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    workdir = tmp_path / "project"
    spec_path = tmp_path / "spec.md"
    workdir.mkdir()
    spec_markdown = "# Task\n\nShip it.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": "loop_relative_registry_writer",
            "name": "Loop Relative Registry Writer",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Ship it.", "checks": [], "constraints": "", "role_notes": {}},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )

    with pytest.raises(ValueError, match="local asset path must be absolute"):
        repository.create_run(
            {
                "id": "run_relative_registry_writer",
                "loop_id": loop["id"],
                "workdir": str(workdir),
                "spec_path": str(spec_path),
                "spec_markdown": spec_markdown,
                "compiled_spec": {"goal": "Ship it.", "checks": [], "constraints": "", "role_notes": {}},
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
                "max_iters": 1,
                "max_role_retries": 1,
                "delta_threshold": 0.1,
                "trigger_window": 1,
                "regression_window": 1,
                "role_models": {},
                "status": "queued",
                "runs_dir": "relative-runs-root",
            }
        )
    with pytest.raises(ValueError, match="local asset path must be absolute"):
        repository.create_alignment_session(
            {
                "id": "align_relative_registry_writer",
                "status": "idle",
                "workdir": str(workdir),
                "bundle_path": "relative-alignment-root/artifacts/bundle.yml",
            }
        )

    assert repository.get_run("run_relative_registry_writer") is None
    assert repository.get_alignment_session("align_relative_registry_writer") is None
    assert repository.list_local_asset_roots(states={"active", "orphaned"}) == []


def test_local_asset_root_registry_internal_writers_share_path_normalizer() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    for module_path in (
        "src/loopora/db_run_records.py",
        "src/loopora/db_alignment_records.py",
        "src/loopora/db_bundle_graph_records.py",
    ):
        source = (repo_root / module_path).read_text(encoding="utf-8")

        assert "INSERT INTO local_asset_roots" in source
        assert "self._normalize_local_asset_path(" in source


def test_local_asset_root_registry_rejects_blank_paths(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="local asset path is required"):
        repository.upsert_local_asset_root(resource_type="run", resource_id="run_blank", path="")

    assert repository.list_local_asset_roots(resource_type="run") == []


def test_repository_schema_mixin_delegates_v3_schema_assets() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    schema_source = (repo_root / "src/loopora/db_schema.py").read_text(encoding="utf-8")
    v3_schema_source = (repo_root / "src/loopora/db_schema_v3.py").read_text(encoding="utf-8")
    design_source = (repo_root / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.db_schema_v3 import" in schema_source
    assert "connection.executescript(V3_SCHEMA_SQL)" in schema_source
    assert "CREATE TABLE IF NOT EXISTS" not in schema_source
    assert "V3_SCHEMA_SQL" in v3_schema_source
    assert "def schema_has_current_v3_shape" in v3_schema_source
    assert "db_schema_v3.py" in design_source


def test_repository_rejects_legacy_schema_for_v3_development_reset(tmp_path: Path) -> None:
    target = tmp_path / "app.db"
    with sqlite3.connect(target) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO loop_definitions (id, name) VALUES ('loop_legacy', 'Legacy Loop')")
        connection.execute("PRAGMA user_version = 1")

    with pytest.raises(LooporaConflictError, match="local App database reset"):
        LooporaRepository(target)


def test_repository_rejects_v2_schema_for_v3_development_reset(tmp_path: Path) -> None:
    target = tmp_path / "app.db"
    with sqlite3.connect(target) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(LooporaConflictError, match="local App database reset"):
        LooporaRepository(target)


def test_create_service_redacts_local_app_state_open_failure(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    private_path = tmp_path / "private" / "app.db"
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setattr(db_module.time, "sleep", lambda _: None)

    def fail_app_db_open(database: object, *_args: object, **_kwargs: object) -> sqlite3.Connection:
        if str(database) == str(app_home / "app.db"):
            raise sqlite3.OperationalError(f"unable to open database file {private_path}: permission denied")
        raise AssertionError(f"unexpected sqlite target: {database!r}")

    monkeypatch.setattr(db_module.sqlite3, "connect", fail_app_db_open)

    with pytest.raises(LooporaError) as error:
        create_service()

    message = str(error.value)
    assert message == LOCAL_APP_STATE_OPEN_ERROR
    assert_local_app_state_open_failure_text(message, private_path)


def test_cli_serve_reports_v3_reset_without_traceback(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project with spaces"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    monkeypatch.chdir(workdir)

    serve_port = str(free_local_port())
    result = CliRunner().invoke(cli.app, ["serve", "--port", serve_port])
    json_result = CliRunner().invoke(cli.app, ["serve", "--port", serve_port, "--json"])
    error_text = result.stderr or result.output

    reset_command = f"{APP_HOME_ENV}={shlex.quote(str(app_home))} loopora dev reset --scope app --workdir {shlex.quote(str(workdir))}"
    recovery_command = f"{APP_HOME_ENV}={shlex.quote(str(app_home))} loopora recovery create --workdir {shlex.quote(str(workdir))}"
    expected_fragments = (
        "Loopora v3 development reset required",
        f"recovery archive before reset: {recovery_command}",
        reset_command,
        f"reset preview: {reset_command}",
        f"reset apply after review: {reset_command} --yes",
        'temporary Web preview: LOOPORA_HOME="$(mktemp -d)" loopora serve --open --host 127.0.0.1 --port',
        "note: Uses a new empty App home",
        "it does not delete, migrate, or repair the blocked App database",
        "app scope resets only local App database files",
        "project .loopora state and managed Agent entries are left alone",
    )
    blocked_fragments = ("--workdir <project>", "Delete LOOPORA_HOME", "Traceback", "cli.command.failed", "schema_version")
    assert (result.exit_code, json_result.exit_code) == (1, 1)
    assert all(fragment in error_text for fragment in expected_fragments)
    assert all(fragment not in error_text for fragment in blocked_fragments)
    json_payload = json.loads(json_result.stdout)
    json_summary = json_payload["serve_startup_recovery_summary"]
    assert [item["kind"] for item in json_payload["next_actions"]][:4] == ["create_recovery_archive", "preview_app_database_reset", "retry_web_start", "use_temporary_app_home"]
    assert (
        json_summary["status"],
        json_payload["start_blocked_reason"],
        json_payload["next_actions"][2]["command_ready"],
        json_summary["readiness_blockers"],
    ) == ("blocked_by_app_state", "app_state_not_ready", False, [APP_STATE_NOT_READY_BLOCKER])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        occupied_port = int(occupied.getsockname()[1])
        blocked = CliRunner().invoke(cli.app, ["serve", "--port", str(occupied_port), "--json"])
        blocked_plain = CliRunner().invoke(cli.app, ["serve", "--port", str(occupied_port)])
    blocked_payload = json.loads(blocked.stdout)
    retry_action = blocked_payload["next_actions"][2]
    assert (blocked.exit_code, blocked_payload["serve_startup_recovery_summary"]["status"]) == (1, "blocked_by_port_conflict")
    assert blocked_payload["serve_startup_recovery_summary"]["readiness_blockers"] == [APP_STATE_NOT_READY_BLOCKER]
    assert [item["kind"] for item in blocked_payload["next_actions"]][:3] == ["create_recovery_archive", "preview_app_database_reset", "retry_web_start_on_alternate_port"]
    assert (retry_action["command_ready"], retry_action["command_blockers"], retry_action["blocked_until"]) == (
        False,
        ["app_state_not_ready"],
        ["app_state_ready"],
    )
    assert "After App state is ready, retry with" in blocked_payload["error"]
    assert " Try `" not in blocked_payload["error"]
    assert "Preview App database reset:" in blocked_plain.output
    assert "Retry Web start on an alternate port after App state is ready:" in blocked_plain.output


def test_cli_serve_reports_local_app_state_open_failure_without_traceback(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    private_path = tmp_path / "private" / "app.db"
    workdir.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.chdir(workdir)
    monkeypatch.setattr(db_module.time, "sleep", lambda _: None)

    def fail_app_db_open(database: object, *_args: object, **_kwargs: object) -> sqlite3.Connection:
        if str(database) == str(app_home / "app.db"):
            raise sqlite3.OperationalError(f"unable to open database file {private_path}: permission denied")
        raise AssertionError(f"unexpected sqlite target: {database!r}")

    monkeypatch.setattr(db_module.sqlite3, "connect", fail_app_db_open)

    result = CliRunner().invoke(cli.app, ["serve", "--port", str(free_local_port())])
    error_text = result.stderr or result.output

    assert result.exit_code == 1
    assert_local_app_state_open_failure_text(error_text, app_home, workdir, private_path)


def test_cli_serve_temporary_preview_preserves_source_checkout_entry(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "target project"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    monkeypatch.chdir(ROOT)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", str(free_local_port()), "--auth-token", "secret-token-123", "--workdir", str(workdir)],
    )
    error_text = result.stderr or result.output
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    assert (
        result.exit_code,
        source_entry.startswith("uv --directory "),
        "--auth-token '<token>'" in error_text,
        "secret-token-123" not in error_text,
        "the real auth token is not printed" in error_text,
    ) == (1, True, True, True, True)
    assert f'temporary Web preview: {APP_HOME_ENV}="$(mktemp -d)" {source_entry} serve --open --host 0.0.0.0 --port' in error_text
    assert f'{APP_HOME_ENV}="$(mktemp -d)" loopora serve' not in error_text
    assert f"--workdir {shlex.quote(str(workdir))}" in error_text


def test_cli_development_reset_json_payload_separates_preview_and_apply(monkeypatch) -> None:
    monkeypatch.delenv(APP_HOME_ENV, raising=False)
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    app = typer.Typer()

    @app.command()
    def command() -> None:
        handle_error(
            LooporaConflictError("Loopora v3 development reset required: existing local database schema version 1 is not compatible."),
            json_output=True,
        )

    result = CliRunner().invoke(app, [])
    payload = json.loads(result.stdout)
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    assert result.exit_code == 1
    assert payload["loop_recovery"] == "development_reset_required"
    assert payload["reset_command"] == f"{source_entry} dev reset --scope app --workdir <project>"
    assert payload["preview_reset_command"] == payload["reset_command"]
    assert payload["apply_reset_command"] == f"{source_entry} dev reset --scope app --workdir <project> --yes"
    assert payload["recovery_archive_command"] == f"{source_entry} recovery create --workdir <project>"
    assert payload["reset_scope"] == "app"
    assert payload["preview_is_destructive"] is False
    assert "local App database files" in payload["scope_description"]
    assert "managed Agent entries are left alone" in payload["scope_description"]
    assert payload["destructive_apply_requires_yes"] is True
    assert "Create and inspect a private recovery archive" in payload["next_step"]
    assert [action["kind"] for action in payload["next_actions"]] == ["create_recovery_archive", "preview_app_database_reset"]


def test_legacy_schema_can_be_archived_and_inspected_before_reset(monkeypatch, tmp_path: Path) -> None:
    app_home, workdir = tmp_path / "loopora-home", tmp_path / "project"
    _mkdirs(app_home, workdir)
    database = app_home / "app.db"
    create_legacy_app_db(database)
    managed = workdir / ".loopora" / "loops" / "legacy" / "record.json"
    managed.parent.mkdir(parents=True)
    managed.write_text('{"legacy": true}\n', encoding="utf-8")
    archive = tmp_path / "legacy-recovery.zip"
    plain_archive = tmp_path / "legacy-recovery-zh.zip"
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    runner = CliRunner()
    created_plain = runner.invoke(cli.app, ["recovery", "create", "--workdir", str(workdir), "--output", str(plain_archive), "--language", "zh-CN"])
    inspected_plain = runner.invoke(cli.app, ["recovery", "inspect", str(plain_archive), "--language", "中文"])
    created = runner.invoke(cli.app, ["recovery", "create", "--workdir", str(workdir), "--output", str(archive), "--language", "zh", "--json"])
    inspected = CliRunner().invoke(cli.app, ["recovery", "inspect", str(archive), "--language", "zh", "--json"])

    assert (created_plain.exit_code, inspected_plain.exit_code, created.exit_code, inspected.exit_code) == (0, 0, 0, 0)
    assert (database.exists(), _schema_user_version(database)) == (True, 1)
    assert all(term in created_plain.stdout for term in ("私有恢复归档：", "共享边界：不可公开", "先验证 checksum", "--language zh"))
    assert all(term in inspected_plain.stdout for term in ("恢复归档：有效", "无写入的重置预览", "找回缺失文件", "重新检查当前就绪状态"))
    assert inspected_plain.stdout.count("--language zh") == 3
    created_payload, payload = json.loads(created.stdout), json.loads(inspected.stdout)
    assert (next(iter(created_payload)), created_payload["recovery_create_summary"]["state"]) == ("recovery_create_summary", "archive_created")
    assert created_payload["next_action_kinds"] == created_payload["next_action_ready_now_kinds"] == ["inspect_recovery_archive"]
    assert (next(iter(payload)), payload["recovery_inspect_summary"]["state"], payload["recovery_purpose_selection_required"]) == ("recovery_inspect_summary", "archive_valid", True)
    expected = ["preview_app_database_reset", "preview_exact_path_restore", "confirm_readiness"]
    assert payload["recovery_choice_kinds"] == payload["next_action_kinds"] == payload["next_action_ready_now_kinds"] == expected
    assert all(action["selection_required"] and action["mutually_exclusive"] and not action["destructive"] for action in payload["next_actions"])
    assert payload["database_schema_version"] == 1
    assert payload["source"]["workdir"] == str(workdir.resolve())
    assert "language" not in payload
    assert "--language" not in created.stdout + inspected.stdout
    assert {item["path"] for item in payload["manifest"]["files"]} >= {
        "app/app.db",
        "project/.loopora/loops/legacy/record.json",
    }


def test_recovery_restore_stays_preview_only_until_yes_and_keeps_chinese_handoff(monkeypatch, tmp_path: Path) -> None:
    app_home, workdir, archive = tmp_path / "home", tmp_path / "project", tmp_path / "recovery.zip"
    _mkdirs(app_home, workdir)
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    LooporaRepository(app_home / "app.db")
    managed = workdir / ".loopora" / "loops" / "saved" / "record.json"
    managed.parent.mkdir(parents=True)
    managed.write_text('{"saved": true}\n', encoding="utf-8")
    runner = CliRunner()
    created = runner.invoke(cli.app, ["recovery", "create", "--workdir", str(workdir), "--output", str(archive), "--json"])
    managed.unlink()

    preview = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--language", "zh-CN"])
    preview_structured = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--json"])
    preview_payload = json.loads(preview_structured.stdout)
    assert created.exit_code == preview.exit_code == 0
    assert not managed.exists()
    assert all(term in preview.stdout for term in ("恢复操作：预览", "计划恢复：1", "审查这次私有精确路径恢复", "--yes --language zh"))
    assert (preview_payload["recovery_restore_summary"]["state"], preview_payload["next_action_kinds"]) == ("restore_preview", ["review_restore_scope", "apply_recovery_restore"])
    assert (preview_payload["next_action_ready_after_actions"], preview_payload["next_actions"][1]["destructive"]) == ({"apply_recovery_restore": "review_restore_scope"}, True)
    applied = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--yes", "--language", "中文"])
    no_op_plain = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--language", "zh"])
    structured = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--language", "zh", "--json"])
    assert applied.exit_code == structured.exit_code == 0
    assert managed.read_text(encoding="utf-8") == '{"saved": true}\n'
    assert all(term in applied.stdout for term in ("恢复操作：已恢复", "已恢复：1", "doctor --workdir", "--language zh"))
    assert "恢复操作：无需恢复" in no_op_plain.stdout
    assert "--yes" not in no_op_plain.stdout
    structured_payload = json.loads(structured.stdout)
    assert (structured_payload["recovery_restore_summary"]["state"], structured_payload["next_action_kinds"]) == ("no_restore_needed", ["confirm_readiness_if_needed"])
    assert all(term not in structured.stdout for term in ("--yes", "--language"))
    assert "language" not in structured_payload
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute("CREATE TABLE recovery_conflict_proof (id TEXT PRIMARY KEY)")
    changed = runner.invoke(cli.app, ["recovery", "restore", str(archive), "--workdir", str(workdir), "--json"])
    changed_payload = json.loads(changed.stdout)
    assert (changed.exit_code, changed_payload["status"]) == (1, "blocked")
    assert (changed_payload["recovery_restore_summary"]["state"], changed_payload["next_action_kinds"]) == ("restore_blocked", ["resolve_restore_conflicts", "retry_restore_preview"])
    assert changed_payload["next_action_ready_after_actions"] == {"retry_restore_preview": "resolve_restore_conflicts"}
    assert str(app_home / "app.db") in changed_payload["conflicts"]


def test_recovery_archive_active_work_routes_through_read_only_status_before_retry(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "home with spaces"
    output = tmp_path / "private archive.zip"
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    repository = LooporaRepository(app_home / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_archive_active", status="running")
    workdir = Path(run["workdir"])
    repository.create_alignment_session(
        {
            "id": "align_archive_active",
            "status": "validating",
            "workdir": str(workdir),
            "bundle_path": str(workdir / ".loopora" / "alignment_sessions" / "align_archive_active" / "candidate.yml"),
        }
    )
    args = ["recovery", "create", "--workdir", str(workdir), "--output", str(output), "--force"]

    structured = CliRunner().invoke(cli.app, [*args, "--json"])
    plain = CliRunner().invoke(cli.app, [*args, "--language", "zh"])

    assert structured.exit_code == plain.exit_code == 1
    payload = json.loads(structured.stdout)
    assert (payload["status"], payload["active_run_count"], payload["active_planning_session_count"]) == (
        "blocked_by_active_work",
        1,
        1,
    )
    assert [action["kind"] for action in payload["next_actions"]] == [
        "inspect_active_work",
        "resolve_active_work",
        "retry_recovery_archive",
    ]
    assert shlex.split(payload["next_actions"][0]["command"])[-3:] == [
        "status",
        "--workdir",
        str(workdir.resolve()),
    ]
    retry = payload["next_actions"][2]
    assert retry["after_action"] == "resolve_active_work"
    assert shlex.split(retry["command"])[-7:] == [
        "recovery",
        "create",
        "--workdir",
        str(workdir.resolve()),
        "--output",
        str(output.resolve()),
        "--force",
    ]
    assert all(term in plain.output for term in ("检查仍在运行或失去 worker 的工作：", "--reconcile 动作", "重试归档：")), plain.output
    assert plain.output.count("--language zh") == 2
    status_result = CliRunner().invoke(cli.app, ["status", "--workdir", str(workdir), "--json"])
    status_payload = json.loads(status_result.stdout)
    assert status_result.exit_code == 0, status_result.stdout
    assert status_payload["read_only"] is True
    assert status_payload["runtime_reconciliation"]["status"] == "not_needed"
    assert repository.get_run(run["id"])["status"] == "running"


def test_cli_adapter_lifecycle_bypasses_app_db_development_reset(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))

    runner = CliRunner()
    check_before_install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    before_payload = json.loads(check_before_install.stdout)

    assert check_before_install.exit_code == 1
    assert check_before_install.stderr == ""
    assert before_payload["kind"] == "agent_check"
    assert before_payload["summary"]["check_status"] == "fail"
    assert before_payload["summary"]["check_recovery"]["state"] == "not_installed"
    assert "development_reset_required" not in check_before_install.stdout
    assert "Loopora v3 development reset required" not in check_before_install.stdout

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    install_payload = json.loads(install.stdout)

    assert install.exit_code == 0
    assert install.stderr == ""
    assert install_payload["status"] == "installed"
    assert install_payload["adapter"] == "codex"
    assert "development_reset_required" not in install.stdout

    check_after_install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    after_payload = json.loads(check_after_install.stdout)

    assert check_after_install.exit_code == 0
    assert check_after_install.stderr == ""
    assert after_payload["kind"] == "agent_check"
    assert after_payload["summary"]["check_status"] == "pass"
    assert after_payload["summary"]["check_recovery"]["state"] == "installed"


def test_cli_init_current_installs_entry_but_blocks_plan_handoff_on_legacy_app_state(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setenv("CODEX_THREAD_ID", "private-thread-id")
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
    runner = CliRunner()

    plain = runner.invoke(cli.app, ["init", "current", "--workdir", str(workdir)])
    structured = runner.invoke(cli.app, ["init", "current", "--workdir", str(workdir), "--json"])

    assert plain.exit_code == structured.exit_code == 1
    assert "Loopora same-Agent setup: needs attention" in plain.stdout
    assert "plan handoff: blocked (app_state_not_ready)" in plain.stdout
    assert "Preview the App-state reset scope" in plain.stdout
    assert "Confirm readiness after recovery" in plain.stdout
    assert "choose a free Web port" not in plain.stdout
    assert plain.stdout.count("loopora doctor") == 1
    assert "private-thread-id" not in plain.stdout
    payload = json.loads(structured.stdout)
    assert payload["status"] == "installed"
    assert payload["setup_ready"] is False
    assert payload["readiness"]["app_state"]["status"] == "development_reset_required"
    assert payload["readiness"]["first_task_handoff_blockers"] == ["app_state_not_ready"]
    assert (workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md").is_file()


def test_cli_diagnose_doctor_bypasses_app_db_development_reset(monkeypatch, tmp_path: Path) -> None:
    app_home, workdir = tmp_path / "loopora-home", tmp_path / "project"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    web_port = free_local_port()

    result = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--json"])
    payload = json.loads(result.stdout)

    assert_doctor_reports_legacy_app_state_before_adapter_install(result, payload)
    assert_doctor_plain_gates_web_start_before_adapter_install(workdir, web_port=web_port)
    assert_doctor_public_gates_web_start_before_adapter_install(app_home, workdir, web_port=web_port)

    install = CliRunner().invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout

    assert_doctor_strict_mode_fails_ready_with_app_warning(workdir, web_port=web_port)


def test_cli_diagnose_doctor_redacts_unreadable_app_db_storage_error(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    _mkdirs(app_home, workdir)
    app_db = app_home / "app.db"
    app_db.write_text("unreadable storage boundary", encoding="utf-8")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    original_connect = app_state_readiness.sqlite3.connect

    def fail_app_db_probe(database: object, *args: object, **kwargs: object) -> sqlite3.Connection:
        if str(database) == f"file:{app_db}?mode=ro":
            raise sqlite3.OperationalError(f"unable to open database file {app_db}: permission denied")
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(app_state_readiness.sqlite3, "connect", fail_app_db_probe)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir), "--json"])
    payload = json.loads(result.stdout)

    assert result.exit_code == 1, result.stdout
    assert payload["diagnose_doctor_summary"]["app_state_status"] == "unreadable"
    assert payload["diagnose_doctor_summary"]["app_state_web_ready"] is False
    assert payload["app_state"]["status"] == "unreadable"
    assert payload["app_state"]["web_ready"] is False
    assert payload["app_state"]["needs_attention"] is True
    assert payload["app_state"]["next_action"] == "inspect_or_reset_app_state"
    assert payload["app_state"]["summary"] == "App database could not be read; inspect or reset local App state."
    assert any(item["kind"] == "inspect_or_reset_app_state" for item in payload["next_action_items"])
    assert "unable to open" not in result.stdout
    assert "permission denied" not in result.stdout

    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir)])
    assert plain.exit_code == 1, plain.stdout
    assert "App state: unreadable (Web ready: no)" in plain.stdout
    assert "note: App database could not be read; inspect or reset local App state." in plain.stdout
    assert "unable to open" not in plain.stdout
    assert "permission denied" not in plain.stdout

    public = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir), "--public-json"])
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)

    assert public.exit_code == 1, public.stdout
    assert public_payload["app_state"]["status"] == "unreadable"
    assert public_payload["app_state"]["next_action"] == "inspect_or_reset_app_state"
    assert str(app_home) not in public_encoded
    assert str(workdir) not in public_encoded
    assert str(app_db) not in public_encoded
    assert "unable to open" not in public_encoded
    assert "permission denied" not in public_encoded


def test_agent_runtime_reset_recovery_uses_json_and_exact_workdir(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project with spaces"
    _mkdirs(app_home, workdir)
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))

    reset_command = f"{APP_HOME_ENV}={shlex.quote(str(app_home))} loopora dev reset --scope app --workdir {shlex.quote(str(workdir))}"
    message = (
        "Goal: test blocked App recovery; Fake-done risks: hidden Web failure; Required evidence: readable recovery; Judgment tradeoffs: keep scope narrow"
    )
    runner = CliRunner()

    plain_plan = runner.invoke(cli.app, ["agent", "codex", "plan", "--workdir", str(workdir), "--message", message])
    json_plan = runner.invoke(
        cli.app,
        ["agent", "codex", "plan", "--workdir", str(workdir), "--message", message, "--json"],
    )
    json_run = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(workdir), "--json"])
    json_next = runner.invoke(cli.app, ["agent", "codex", "next", "--workdir", str(workdir), "--json"])
    result_file = workdir / "result.json"
    result_file.write_text(json.dumps({"loopora_host_dispatch": {}, "result": {}}), encoding="utf-8")
    json_submit = runner.invoke(
        cli.app,
        ["agent", "codex", "submit", "--result-file", str(result_file), "--workdir", str(workdir), "--json"],
    )

    assert plain_plan.exit_code == 1, plain_plan.stdout
    assert reset_command in plain_plan.output
    assert f"reset apply after review: {reset_command} --yes" in plain_plan.output
    assert "app scope resets only local App database files" in plain_plan.output
    assert "--workdir <project>" not in plain_plan.output

    for result in (json_plan, json_run, json_next, json_submit):
        payload = json.loads(result.stdout)
        assert result.exit_code == 1, result.stdout
        assert payload["loop_recovery"] == "development_reset_required"
        assert payload["reset_command"] == reset_command
        assert payload["apply_reset_command"] == f"{reset_command} --yes"
        assert payload["reset_scope"] == "app"
        assert payload["preview_is_destructive"] is False
        assert "project .loopora state" in payload["scope_description"]
        assert "--workdir <project>" not in result.stdout


def test_direct_loop_create_commands_report_same_home_reset_recovery(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project with spaces"
    spec_path = tmp_path / "spec.md"
    _mkdirs(app_home, workdir)
    spec_path.write_text("# Task\n\nShip it.\n", encoding="utf-8")
    create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    reset_command = f"{APP_HOME_ENV}={shlex.quote(str(app_home))} {source_entry} dev reset --scope app --workdir {shlex.quote(str(workdir))}"
    runner = CliRunner()

    root_run = runner.invoke(cli.app, ["run", "--spec", str(spec_path), "--workdir", str(workdir)])
    loops_create = runner.invoke(cli.app, ["loops", "create", "--spec", str(spec_path), "--workdir", str(workdir)])

    for result in (root_run, loops_create):
        error_text = result.stderr or result.output
        assert result.exit_code == 1, result.stdout
        assert "Loopora v3 development reset required" in error_text
        assert reset_command in error_text
        assert f"reset apply after review: {reset_command} --yes" in error_text
        assert "project .loopora state and managed Agent entries are left alone" in error_text
        assert "--workdir <project>" not in error_text
        assert "Traceback" not in error_text


def test_direct_loop_create_commands_explain_missing_workdir_before_service(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    missing_workdir = tmp_path / "missing project"
    spec_path.write_text("# Task\n\nShip it.\n", encoding="utf-8")
    runner = CliRunner()

    root_run = runner.invoke(cli.app, ["run", "--spec", str(spec_path), "--workdir", str(missing_workdir)])
    loops_create = runner.invoke(cli.app, ["loops", "create", "--spec", str(spec_path), "--workdir", str(missing_workdir)])

    for result, action, retry_fragment in [
        (root_run, "run", "loopora run --spec"),
        (loops_create, "create", "loopora loops create --spec"),
    ]:
        error_text = result.stderr or result.output
        assert result.exit_code == 1, error_text
        assert not missing_workdir.exists()
        assert "Invalid value for '--workdir'" not in error_text
        assert f"Loopora Loop {action} is blocked" in error_text
        assert "project directory state: missing" in error_text
        assert "Target project directory does not exist yet" in error_text
        assert f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}" in error_text
        assert retry_fragment in error_text
        assert "loopora doctor --workdir" in error_text
        assert error_text.index(retry_fragment) < error_text.index("loopora doctor --workdir")


def test_direct_loop_create_commands_reject_file_workdir_before_service(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    workdir_file = tmp_path / "not-a-project"
    spec_path.write_text("# Task\n\nShip it.\n", encoding="utf-8")
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    original = workdir_file.read_text(encoding="utf-8")

    result = CliRunner().invoke(cli.app, ["loops", "create", "--spec", str(spec_path), "--workdir", str(workdir_file)])

    error_text = result.stderr or result.output
    assert result.exit_code == 1, error_text
    assert workdir_file.read_text(encoding="utf-8") == original
    assert "Invalid value for '--workdir'" not in error_text
    assert "project directory state: not_directory" in error_text
    assert "Target project path exists but is not a directory" in error_text
    assert "Choose an existing project directory" in error_text
    assert "mkdir -p" not in error_text


def test_run_schema_persists_task_verdict_separately_from_raw_verdict(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_task_verdict", status="running")

    with repository.transaction() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(loop_runs)").fetchall()}
    assert "task_verdict_json" in columns

    repository.update_run(
        run["id"],
        status="succeeded",
        last_verdict={"passed": True, "decision_summary": "Raw GateKeeper pass."},
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Evidence-backed task pass.",
            "buckets": {
                "proven": [],
                "weak": [],
                "unproven": [],
                "blocking": [],
                "residual_risk": [],
            },
        },
    )

    refreshed = repository.get_run(run["id"])

    assert refreshed["last_verdict_json"]["decision_summary"] == "Raw GateKeeper pass."
    assert refreshed["task_verdict_json"]["summary"] == "Evidence-backed task pass."
