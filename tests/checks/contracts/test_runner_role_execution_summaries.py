from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop


def test_plateau_run_records_challenger_execution_summary(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="plateau")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Plateau Loop",
        workflow={"preset": "repair_loop"},
        max_iters=4,
    )

    run = service.rerun(loop["id"])

    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    challenger_summaries = [
        event
        for event in events
        if event["event_type"] == "role_execution_summary" and event["payload"].get("role") == "challenger"
    ]
    verifier_summaries = [
        event
        for event in events
        if event["event_type"] == "role_execution_summary" and event["payload"].get("role") == "verifier"
    ]

    assert challenger_summaries
    assert verifier_summaries
    assert all(event["payload"]["duration_ms"] >= 0 for event in challenger_summaries + verifier_summaries)
