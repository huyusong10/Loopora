from __future__ import annotations

from pathlib import Path

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


def test_loop_deletion_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    deletion_source = (REPO_ROOT / "src" / "loopora" / "service_loop_deletion.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_loop_deletion import ServiceLoopDeletionMixin" in lifecycle_source
    assert "def delete_loop" not in lifecycle_source
    assert "def delete_loop" in deletion_source
    assert "def _mark_local_asset_cleanup_by_path" in deletion_source
    assert "service_loop_deletion.py" in design_source
