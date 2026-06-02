from __future__ import annotations

import json
from pathlib import Path

from loopora.service import LooporaService

from runner_helpers import _create_loop


def test_early_execute_run_crash_is_persisted_as_failed(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Early Crash Loop")
    run = service.start_run(loop["id"])

    service.executor_factory = lambda: (_ for _ in ()).throw(RuntimeError("executor boot failed"))  # type: ignore[assignment]

    failed = service.execute_run(run["id"])

    assert failed["status"] == "failed"
    assert failed["error_message"] == "executor boot failed"
    assert run["id"] not in LooporaService._process_active_runs
    summary = Path(failed["runs_dir"]) / "summary.md"
    assert "Execution crashed unexpectedly." in summary.read_text(encoding="utf-8")


def test_service_startup_marks_stale_active_runs_stopped(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Stale Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="running",
        runner_pid=999999,
        active_role="tester",
        started_at="2026-04-13T08:00:00+00:00",
    )

    restarted = LooporaService(
        repository=service.repository,
        settings=service.settings,
        executor_factory=service.executor_factory,
    )
    recovered = restarted.get_run(run["id"])

    assert recovered["status"] == "stopped"
    assert recovered["finished_at"] is not None
    assert recovered["runner_pid"] is None
    assert recovered["child_pid"] is None
    assert "Recovered stale run" in (recovered["error_message"] or "")
    assert recovered["task_verdict"]["status"] == "not_evaluated"
    assert recovered["task_verdict"]["source"] == "run_status"
    verdict_path = Path(recovered["runs_dir"]) / "evidence" / "task_verdict.json"
    assert json.loads(verdict_path.read_text(encoding="utf-8")) == recovered["task_verdict"]

    events = restarted.repository.list_events(run["id"], after_id=0, limit=1000)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"].get("reason") == "Recovered stale run after service startup."
        and event["payload"]["task_verdict_status"] == "not_evaluated"
        and event["payload"]["task_verdict_source"] == "run_status"
        and event["payload"]["task_verdict_summary"] == recovered["task_verdict"]["summary"]
        for event in events
    )

    fresh_run = restarted.rerun(loop["id"])
    assert fresh_run["status"] == "succeeded"
