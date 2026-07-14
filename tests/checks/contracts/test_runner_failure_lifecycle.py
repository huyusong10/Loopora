from __future__ import annotations

from pathlib import Path

from runner_helpers import (
    _create_loop,
    _force_run_missing_strategy_snapshot,
)
from loopora.service_runner_failure_handling import RUN_LOCAL_RUNTIME_ERROR


def test_unexpected_run_error_marks_run_failed(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Crash Loop")
    run = service.start_run(loop["id"])

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    service._resolve_run_checks = explode  # type: ignore[method-assign]

    failed = service.execute_run(run["id"])

    assert failed["status"] == "failed"
    assert failed["error_message"] == "boom"
    summary = Path(failed["runs_dir"]) / "summary.md"
    assert "Execution crashed unexpectedly." in summary.read_text(encoding="utf-8")
    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert any(event["event_type"] == "run_aborted" for event in events)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "failed"
        and event["payload"]["reason"] == "crashed"
        and event["payload"]["task_verdict_status"] == "not_evaluated"
        and event["payload"].get("task_verdict_summary")
        for event in events
    )


def test_unexpected_run_os_error_uses_stable_local_runtime_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Crash Loop")
    run = service.start_run(loop["id"])
    private_path = tmp_path / "private" / "runner-context.json"

    def explode(*_args, **_kwargs):
        raise OSError(f"permission denied: {private_path}")

    service._resolve_run_checks = explode  # type: ignore[method-assign]

    failed = service.execute_run(run["id"])

    assert failed["status"] == "failed"
    assert failed["error_message"] == RUN_LOCAL_RUNTIME_ERROR
    assert "permission denied" not in failed["error_message"]
    assert str(private_path) not in failed["error_message"]
    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    aborted = next(event for event in events if event["event_type"] == "run_aborted")
    assert aborted["payload"]["error"] == RUN_LOCAL_RUNTIME_ERROR


def test_empty_strategy_snapshot_fails_closed_without_legacy_runtime(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Missing Strategy Loop")
    run = service.start_run(loop["id"])
    _force_run_missing_strategy_snapshot(service, run["id"])

    failed = service.execute_run(run["id"])

    assert failed["status"] == "failed"
    assert failed["error_message"] == "Run has no strategy snapshot; legacy execution runtime has been removed."
    assert not hasattr(service, "_execute_legacy_run")
    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert any(event["event_type"] == "run_aborted" for event in events)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "failed"
        and event["payload"].get("reason") == "missing_strategy_snapshot"
        for event in events
    )
