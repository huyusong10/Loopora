from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.db import LooporaRepository
from loopora.db_schema import CURRENT_SCHEMA_VERSION
from loopora.service_types import LooporaConflictError

from db_test_support import _create_run


def _schema_user_version(path: Path) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])


def test_repository_initializes_schema_user_version(tmp_path: Path) -> None:
    target = tmp_path / "app.db"

    LooporaRepository(target)
    LooporaRepository(target)

    assert _schema_user_version(target) == CURRENT_SCHEMA_VERSION


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

    with pytest.raises(LooporaConflictError, match="Loopora v3 development reset required"):
        LooporaRepository(target)


def test_repository_rejects_v2_schema_for_v3_development_reset(tmp_path: Path) -> None:
    target = tmp_path / "app.db"
    with sqlite3.connect(target) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 2")

    with pytest.raises(LooporaConflictError, match="Loopora v3 development reset required"):
        LooporaRepository(target)


def test_cli_serve_reports_v3_reset_without_traceback(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    app_home.mkdir()
    _create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))

    result = CliRunner().invoke(cli.app, ["serve"])
    error_text = result.stderr or result.output

    assert result.exit_code == 1
    assert "Loopora v3 development reset required" in error_text
    assert "loopora dev reset --workdir <project>" in error_text
    assert "Traceback" not in error_text
    assert "cli.command.failed" not in error_text
    assert "schema_version" not in error_text


def test_cli_init_json_reports_v3_reset_without_adapter_conflict(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    _create_legacy_app_db(app_home / "app.db")
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))

    runner = CliRunner()
    for args in (
        ["init", "codex", "--workdir", str(workdir), "--json"],
        ["init", "codex", "--workdir", str(workdir), "--check", "--json"],
    ):
        result = runner.invoke(cli.app, args)
        payload = json.loads(result.stdout)

        assert result.exit_code == 1
        assert result.stderr == ""
        assert payload["loop_recovery"] == "development_reset_required"
        assert payload["reset_command"] == "loopora dev reset --workdir <project>"
        assert "Loopora v3 development reset required" in payload["message"]
        assert "adapter_install_conflict" not in result.stdout
        assert "install_conflict" not in result.stdout


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


def _create_legacy_app_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 1")
