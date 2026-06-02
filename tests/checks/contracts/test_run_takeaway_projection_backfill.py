from __future__ import annotations

from pathlib import Path

from run_takeaway_projection_service_test_support import (
    create_takeaway_loop,
    rerun_takeaway_loop,
    restarted_service,
)


def test_run_takeaway_projection_backfills_existing_terminal_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Snapshot Backfill Loop",
        max_iters=2,
    )
    with service.repository.transaction() as connection:
        connection.execute("DELETE FROM run_takeaway_projections WHERE run_id = ?", (run["id"],))

    snapshot = restarted_service(service).run_observation_snapshot(run["id"])

    assert 0 < snapshot["key_takeaways"]["source_event_id"] <= snapshot["latest_event_id"]
    assert snapshot["key_takeaways"]["iteration_count"] >= 1


def test_run_takeaway_projection_backfills_terminal_runs_with_only_generic_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_takeaway_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Minimal Snapshot Backfill Loop",
        max_iters=2,
    )
    run = service.start_run(loop["id"])
    latest_event_id = service.repository.latest_event_id(run["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nLifecycle closed before any role takeaway event was written.\n",
    )
    with service.repository.transaction() as connection:
        connection.execute("DELETE FROM workdir_locks WHERE run_id = ?", (run["id"],))
        connection.execute("DELETE FROM run_takeaway_projections WHERE run_id = ?", (run["id"],))

    snapshot = restarted_service(service).run_observation_snapshot(run["id"])

    assert snapshot["latest_event_id"] == latest_event_id
    assert snapshot["key_takeaways"]["source_event_id"] == latest_event_id
    assert snapshot["key_takeaways"]["run_status"] == "succeeded"
    assert snapshot["key_takeaways"]["iteration_count"] == 0
    assert "Lifecycle closed before any role takeaway event" in snapshot["key_takeaways"]["latest_summary"]
