from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

from web_run_observation_snapshot_test_support import create_snapshot_loop, observation_client


EXTRA_PROGRESS_EVENT_COUNT = 2050
EXTRA_TIMELINE_EVENT_COUNT = 45
SNAPSHOT_CONSOLE_EVENT_LIMIT = 160
SNAPSHOT_PROGRESS_EVENT_LIMIT = 2000
SNAPSHOT_TIMELINE_EVENT_LIMIT = 40


def test_api_run_observation_snapshot_is_bounded_and_redacted(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_snapshot_loop(service, sample_spec_file, sample_workdir, name="Snapshot Loop")
    run = service.rerun(loop["id"])

    for index in range(EXTRA_TIMELINE_EVENT_COUNT):
        service.repository.append_event(
            run["id"],
            "run_finished",
            {"status": "succeeded", "reason": f"snapshot timeline {index}", "iter": index},
        )
    for index in range(EXTRA_PROGRESS_EVENT_COUNT):
        service.repository.append_event(
            run["id"],
            "role_started",
            {"role": "generator", "step_id": "builder_step", "iter": index},
            role="generator",
        )
    marker = "UNIQUE-SNAPSHOT-SECRET-MARKER"
    redacted_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {
            "type": "command",
            "message": "uv run pytest -q",
            "prompt": marker,
            "json_schema": {"marker": marker},
        },
        role="generator",
    )

    client = observation_client(service)
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["run"]["id"] == run["id"]
    assert payload["latest_event_id"] == redacted_event["id"]
    assert len(payload["timeline_events"]) == SNAPSHOT_TIMELINE_EVENT_LIMIT
    assert len(payload["console_events"]) == SNAPSHOT_CONSOLE_EVENT_LIMIT
    assert len(payload["progress_events"]) == SNAPSHOT_PROGRESS_EVENT_LIMIT
    assert payload["key_takeaways"]["run_status"] == "succeeded"
    assert 0 < payload["key_takeaways"]["source_event_id"] <= payload["latest_event_id"]
    assert marker not in json.dumps(payload, ensure_ascii=False)

    html_response = client.get(f"/runs/{run['id']}")
    assert html_response.status_code == HTTPStatus.OK
    assert marker not in html_response.text
    timeline_text = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    assert marker not in timeline_text
    assert "uv run pytest -q" in json.dumps(payload["console_events"], ensure_ascii=False)
