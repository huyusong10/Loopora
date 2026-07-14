from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source

from loopora.branding import state_dir_for_workdir
import loopora.service_cleanup_diagnostics as cleanup_diagnostics

from runner_helpers import _create_loop


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_loop_delete_logs_artifact_cleanup_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    log_calls: list[dict] = []

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(run["runs_dir"]):
            raise OSError("run dir locked")

    def capture_log_event(_logger, _level, event, message, **context):
        log_calls.append({"event": event, "message": message, "context": context})

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", capture_log_event)
    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert any(
        call["event"] == "service.cleanup.failed"
        and call["context"].get("operation") == "loop_artifact_delete"
        and call["context"].get("owner_id") == loop["id"]
        for call in log_calls
    )


def test_loop_delete_logs_registry_mark_failure_without_failing(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    log_calls: list[dict] = []

    def fail_registry_mark(*, path: Path, state: str) -> int:
        assert state in {"cleaned", "orphaned"}
        if Path(path) == Path(run["runs_dir"]):
            raise RuntimeError("registry write failed")
        return 1

    def capture_log_event(_logger, _level, event, message, **context):
        log_calls.append({"event": event, "message": message, "context": context})

    monkeypatch.setattr(service.repository, "mark_local_asset_root_state_by_path", fail_registry_mark)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", capture_log_event)
    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert any(
        call["event"] == "service.cleanup.failed"
        and call["context"].get("operation") == "loop_artifact_delete_registry_mark"
        and call["context"].get("owner_id") == loop["id"]
        for call in log_calls
    )


def test_loop_delete_uses_normalized_saved_workdir_for_loop_artifacts(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    loop_artifact_dir = state_dir_for_workdir(sample_workdir) / "loops" / loop["id"]
    assert loop_artifact_dir.exists()
    monkeypatch.chdir(sample_workdir.parent)
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", (sample_workdir.name, loop["id"]))

    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert not loop_artifact_dir.exists()


def test_loop_delete_does_not_remove_current_directory_artifact_for_blank_saved_workdir(
    monkeypatch,
    tmp_path: Path,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    wrong_cwd = tmp_path / "wrong-cwd"
    fake_loop_dir = state_dir_for_workdir(wrong_cwd) / "loops" / loop["id"]
    fake_loop_dir.mkdir(parents=True)
    sentinel = fake_loop_dir / "sentinel.txt"
    sentinel.write_text("must survive\n", encoding="utf-8")
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", ("", loop["id"]))
    monkeypatch.chdir(wrong_cwd)

    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert sentinel.read_text(encoding="utf-8") == "must survive\n"


def test_loop_delete_preview_reports_scope_without_mutating(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.start_run(loop["id"])

    preview = service.preview_loop_delete(loop["id"])

    assert preview["status"] == "dry_run"
    assert preview["delete_allowed"] is False
    assert preview["would_delete"] == {"loop": loop["id"], "run_count": 1, "run_ids": [run["id"]]}
    assert preview["blocked_by_active_runs"] == [run["id"]]
    assert service.repository.get_loop(loop["id"]) is not None
    assert service.repository.get_run(run["id"]) is not None


def test_loop_deletion_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    deletion_source = (REPO_ROOT / "src" / "loopora" / "service_loop_deletion.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_loop_deletion import ServiceLoopDeletionMixin" in lifecycle_source
    assert "def delete_loop" not in lifecycle_source
    assert "def delete_loop" in deletion_source
    assert "def _mark_local_asset_cleanup_by_path" in deletion_source
    assert "loop_artifact_dir_for_ready_workdir" in deletion_source
    assert "service_loop_deletion.py" in design_source
