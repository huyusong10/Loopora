from __future__ import annotations

import os
from pathlib import Path

from runner_helpers import _create_loop


def test_get_run_recovers_local_orphaned_active_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Orphan Loop")
    run = service.start_run(loop["id"])
    service._local_run_orphan_grace_seconds = lambda: 0.0  # type: ignore[method-assign]
    service.repository.update_run(
        run["id"],
        status="running",
        runner_pid=os.getpid(),
        active_role="generator",
        started_at="2026-04-13T08:00:00+00:00",
    )

    service._threads.pop(run["id"], None)

    recovered = service.get_run(run["id"])

    assert recovered["status"] == "failed"
    assert recovered["runner_pid"] is None
    assert recovered["child_pid"] is None
    assert "Recovered orphaned run" in (recovered["error_message"] or "")
    assert recovered["task_verdict"]["status"] == "not_evaluated"
    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert any(event["event_type"] == "run_aborted" for event in events)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "failed"
        and event["payload"]["reason"] == "orphaned_worker"
        and event["payload"]["task_verdict_status"] == "not_evaluated"
        for event in events
    )
