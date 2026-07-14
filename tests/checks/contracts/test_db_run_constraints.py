from __future__ import annotations

from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.service_types import ACTIVE_WORKDIR_CONFLICT_MESSAGE, LooporaConflictError
from loopora.settings import configure_logging

from db_test_support import _create_run, _read_service_log_records


MISSING_CHILD_PID = 999999


def test_create_run_rejects_second_active_run_for_workdir(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    first_run = _create_run(repository, tmp_path, run_id="run_active_first", status="queued")
    workdir = Path(first_run["workdir"])
    spec_path = tmp_path / "second-spec.md"
    spec_markdown = "# Task\n\nShip it again.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    second_loop = repository.create_loop(
        {
            "id": "loop_active_second",
            "name": "Loop Active Second",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Ship it again.", "checks": [], "constraints": "", "role_notes": {}},
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
    second_run_dir = workdir / ".loopora" / "runs" / "run_active_second"
    second_run_dir.mkdir(parents=True)

    with pytest.raises(LooporaConflictError, match="another active run is already using") as exc_info:
        repository.create_run(
            {
                "id": "run_active_second",
                "loop_id": second_loop["id"],
                "workdir": str(workdir),
                "spec_path": str(spec_path),
                "spec_markdown": spec_markdown,
                "compiled_spec": {"goal": "Ship it again.", "checks": [], "constraints": "", "role_notes": {}},
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
                "max_iters": 1,
                "max_role_retries": 1,
                "delta_threshold": 0.1,
                "trigger_window": 1,
                "regression_window": 1,
                "role_models": {},
                "status": "queued",
                "runs_dir": str(second_run_dir),
                "summary_md": "# Loopora Run Summary\n\nQueued.\n",
            }
        )
    assert str(exc_info.value) == ACTIVE_WORKDIR_CONFLICT_MESSAGE
    assert str(workdir) not in str(exc_info.value)


def test_create_run_rejects_legacy_relative_active_workdir(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    first_run = _create_run(repository, tmp_path, run_id="run_legacy_relative_first", status="queued")
    workdir = Path(first_run["workdir"])
    monkeypatch.chdir(workdir.parent)
    with repository.transaction() as connection:
        connection.execute("UPDATE loop_runs SET workdir = ? WHERE id = ?", (workdir.name, first_run["id"]))

    spec_path = tmp_path / "relative-second-spec.md"
    spec_markdown = "# Task\n\nShip it again.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    second_loop = repository.create_loop(
        {
            "id": "loop_relative_active_second",
            "name": "Loop Relative Active Second",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Ship it again.", "checks": [], "constraints": "", "role_notes": {}},
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
    second_run_dir = workdir / ".loopora" / "runs" / "run_relative_active_second"
    second_run_dir.mkdir(parents=True)

    with pytest.raises(LooporaConflictError, match="another active run is already using") as exc_info:
        repository.create_run(
            {
                "id": "run_relative_active_second",
                "loop_id": second_loop["id"],
                "workdir": str(workdir),
                "spec_path": str(spec_path),
                "spec_markdown": spec_markdown,
                "compiled_spec": {"goal": "Ship it again.", "checks": [], "constraints": "", "role_notes": {}},
                "model": "gpt-5.4",
                "reasoning_effort": "medium",
                "max_iters": 1,
                "max_role_retries": 1,
                "delta_threshold": 0.1,
                "trigger_window": 1,
                "regression_window": 1,
                "role_models": {},
                "status": "queued",
                "runs_dir": str(second_run_dir),
                "summary_md": "# Loopora Run Summary\n\nQueued.\n",
            }
        )
    assert str(exc_info.value) == ACTIVE_WORKDIR_CONFLICT_MESSAGE


def test_claim_run_slot_rejects_legacy_relative_workdir_lock(tmp_path: Path, monkeypatch) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    locked_run = _create_run(repository, tmp_path, run_id="run_locked_relative", status="running")
    candidate_run = _create_run(repository, tmp_path, run_id="run_lock_candidate", status="queued")
    candidate_workdir = Path(candidate_run["workdir"])
    monkeypatch.chdir(candidate_workdir.parent)
    with repository.transaction() as connection:
        connection.execute("UPDATE loop_runs SET workdir = ? WHERE id = ?", (str(candidate_workdir), candidate_run["id"]))
        connection.execute("UPDATE loop_runs SET workdir = ? WHERE id = ?", (candidate_workdir.name, locked_run["id"]))
        connection.execute(
            "INSERT INTO workdir_locks (workdir, run_id, acquired_at) VALUES (?, ?, ?)",
            (candidate_workdir.name, locked_run["id"], "2026-01-01T00:00:00Z"),
        )

    assert repository.claim_run_slot(candidate_run["id"], max_concurrent_runs=10) is False
    assert repository.get_run(candidate_run["id"])["status"] == "queued"


def test_send_stop_signal_clears_stale_child_pid_and_logs_warning(tmp_path: Path, monkeypatch) -> None:
    configure_logging()
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_stale", status="running")
    repository.update_run(run["id"], child_pid=999999)

    def missing_process(_pid: int, _signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr("loopora.db.os.kill", missing_process)

    assert repository.send_stop_signal(run["id"]) is True

    refreshed = repository.get_run(run["id"])
    assert refreshed["child_pid"] is None
    record = next(
        item
        for item in _read_service_log_records()
        if item["event"] == "db.run.stop_signal_skipped" and item["run_id"] == run["id"]
    )
    assert record["level"] == "WARNING"
    assert record["context"]["child_pid"] == MISSING_CHILD_PID
    assert record["context"]["reason"] == "process_not_found"
