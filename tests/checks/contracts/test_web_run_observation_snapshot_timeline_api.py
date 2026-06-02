from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from loopora.run_observation_events import PROGRESS_EVENT_TYPES, TIMELINE_EVENT_TYPES

from web_run_observation_snapshot_test_support import create_snapshot_loop, observation_client


def test_api_run_observation_snapshot_projects_stable_timeline_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_snapshot_loop(service, sample_spec_file, sample_workdir, name="Parallel Snapshot Loop")
    run = service.start_run(loop["id"])
    service.repository.append_event(
        run["id"],
        "role_request_prepared",
        {"role_name": "Builder", "role": "builder", "step_id": "build", "iter": 0},
        role="builder",
    )
    service.repository.append_event(
        run["id"],
        "step_instruction_context_prepared",
        {"step_id": "build", "context_path": "steps/build/step_instruction_context.json"},
        role="builder",
    )
    payload = {
        "iter": 0,
        "parallel_group": "inspection_pack",
        "step_orders": [1, 2],
        "step_ids": ["inspect_a", "inspect_b"],
    }
    service.repository.append_event(run["id"], "parallel_group_started", payload)
    service.repository.append_event(run["id"], "parallel_group_finished", payload)
    service.repository.append_event(
        run["id"],
        "control_triggered",
        {"signal": "gatekeeper_rejected", "role_id": "guide", "reason": "needs repair"},
    )
    service.repository.append_event(
        run["id"],
        "run_finished",
        {"status": "succeeded", "reason": "legacy_terminal_event_without_verdict"},
    )

    assert "role_request_prepared" in TIMELINE_EVENT_TYPES
    assert "step_instruction_context_prepared" in TIMELINE_EVENT_TYPES
    assert "control_triggered" in TIMELINE_EVENT_TYPES
    assert "parallel_group_started" in TIMELINE_EVENT_TYPES
    assert "run_finished" in TIMELINE_EVENT_TYPES
    assert "parallel_group_started" in PROGRESS_EVENT_TYPES
    assert "step_instruction_context_prepared" in PROGRESS_EVENT_TYPES
    assert "run_finished" in PROGRESS_EVENT_TYPES
    client = observation_client(service)
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == HTTPStatus.OK
    snapshot = response.json()
    timeline_events = [
        event for event in snapshot["timeline_events"] if event["event_type"].startswith("parallel_group_")
    ]
    timeline_event_by_type = {event["event_type"]: event for event in snapshot["timeline_events"]}
    progress_types = [event["event_type"] for event in snapshot["progress_events"]]
    assert timeline_event_by_type["role_request_prepared"]["title"] == "Role request prepared"
    assert timeline_event_by_type["step_instruction_context_prepared"]["title"] == "StepInstruction context prepared"
    assert timeline_event_by_type["step_instruction_context_prepared"]["detail"] == "build"
    assert timeline_event_by_type["control_triggered"]["title"] == "Control triggered"
    assert [event["event_type"] for event in timeline_events] == ["parallel_group_started", "parallel_group_finished"]
    assert timeline_events[0]["title"] == "Parallel review started"
    assert timeline_events[0]["detail"] == "inspection_pack, steps=2"
    assert timeline_event_by_type["run_finished"]["detail"] == (
        "legacy_terminal_event_without_verdict, task_verdict_status=not_evaluated"
    )
    assert "parallel_group_started" in progress_types
    assert "parallel_group_finished" in progress_types
    assert "run_finished" in progress_types
