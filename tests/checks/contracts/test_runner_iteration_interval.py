from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop


def test_iteration_interval_emits_wait_events_between_rounds(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Timed Round Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=2,
        iteration_interval_seconds=0.01,
    )

    run = service.rerun(loop["id"])

    events = service.stream_events(run["id"], limit=200)
    assert any(event["event_type"] == "iteration_wait_started" for event in events)
    assert any(event["event_type"] == "iteration_wait_finished" for event in events)
