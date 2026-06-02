from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path

import pytest

from run_takeaway_projection_service_test_support import (
    rerun_takeaway_loop,
    set_first_handoff_summary,
    takeaway_client,
)


def test_api_run_observation_snapshot_uses_persisted_takeaway_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(service, sample_spec_file, sample_workdir, name="Snapshot Projection Loop")
    marker = "LIVE-ARTIFACT-UPDATE-AFTER-PROJECTION"
    set_first_handoff_summary(run, marker)
    late_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "late non-projection event"},
        role="generator",
    )

    client = takeaway_client(service)
    snapshot_response = client.get(f"/api/runs/{run['id']}/observation-snapshot")
    live_response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert snapshot_response.status_code == HTTPStatus.OK
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["latest_event_id"] == late_event["id"]
    assert snapshot_payload["key_takeaways"]["source_event_id"] < snapshot_payload["latest_event_id"]
    assert marker not in json.dumps(snapshot_payload["key_takeaways"], ensure_ascii=False)
    assert live_response.status_code == HTTPStatus.OK
    assert marker in json.dumps(live_response.json(), ensure_ascii=False)


def test_api_run_observation_snapshot_normalizes_legacy_takeaway_projection_shape(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(service, sample_spec_file, sample_workdir, name="Legacy Snapshot Projection Loop")
    legacy_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "legacy projection cutoff"},
        role="generator",
    )
    service.repository.record_run_takeaway_projection(
        run["id"],
        legacy_event["id"],
        {
            "run_status": "succeeded",
            "task_verdict": {"status": "passed", "source": "gatekeeper", "summary": "legacy shape", "buckets": {}},
            "iterations": [],
        },
    )

    response = takeaway_client(service).get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == HTTPStatus.OK
    key_takeaways = response.json()["key_takeaways"]
    assert key_takeaways["source_event_id"] == legacy_event["id"]
    assert key_takeaways["task_verdict_path"] == ""
    assert key_takeaways["evidence_buckets"] == {}
    assert key_takeaways["evidence_coverage"]["status"] == "pending"
    assert key_takeaways["evidence_coverage"]["coverage_path"] == ""
    assert key_takeaways["evidence_manifest"]["manifest_path"] == ""
    assert key_takeaways["evidence_manifest"]["claim_count"] == 0
    assert key_takeaways["evidence_count"] == 0


@pytest.mark.parametrize("event_type", ["control_completed", "control_failed"])
def test_control_events_refresh_persisted_takeaway_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    event_type: str,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(service, sample_spec_file, sample_workdir, name="Control Projection Loop")
    control_marker = f"{event_type}-snapshot-marker"
    later_marker = f"{event_type}-later-marker"
    set_first_handoff_summary(run, control_marker)
    control_event = service.append_run_event(
        run["id"],
        event_type,
        {"control_id": "audit_control", "signal": "no_evidence_progress", "evidence_refs": []},
    )
    set_first_handoff_summary(run, later_marker)
    late_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "late non-projection event"},
        role="generator",
    )

    response = takeaway_client(service).get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    key_takeaways_text = json.dumps(payload["key_takeaways"], ensure_ascii=False)
    assert payload["latest_event_id"] == late_event["id"]
    assert payload["key_takeaways"]["source_event_id"] == control_event["id"]
    assert control_marker in key_takeaways_text
    assert later_marker not in key_takeaways_text
