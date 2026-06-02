from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner_helpers import _create_loop


@pytest.mark.parametrize("max_fires_per_run", [0, True, "2"])
def test_workflow_run_rejects_invalid_persisted_control_fire_limit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    max_fires_per_run: object,
) -> None:
    service = service_factory(scenario="success")
    run, events = rerun_with_corrupted_workflow(
        service,
        (sample_spec_file, sample_workdir),
        name="Corrupted Control Loop",
        workflow=control_workflow(),
        corruption=(("controls", 0, "max_fires_per_run"), max_fires_per_run),
    )

    assert run["status"] == "failed"
    assert "max_fires_per_run" in run["error_message"]
    assert not any(event["event_type"] == "control_triggered" for event in events)


@pytest.mark.parametrize("limit", [True, "12"])
def test_workflow_run_rejects_invalid_persisted_evidence_query_limit(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    limit: object,
) -> None:
    service = service_factory(scenario="success")
    run, events = rerun_with_corrupted_workflow(
        service,
        (sample_spec_file, sample_workdir),
        name="Corrupted Evidence Query Loop",
        workflow=gatekeeper_workflow(evidence_query=True),
        corruption=(("steps", 1, "inputs", "evidence_query", "limit"), limit),
    )

    assert run["status"] == "failed"
    assert "evidence_query.limit must be an integer" in run["error_message"]
    assert not any(event["event_type"] == "role_execution_summary" and event["payload"].get("archetype") == "gatekeeper" for event in events)


def test_workflow_run_rejects_invalid_persisted_step_action_policy(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run, events = rerun_with_corrupted_workflow(
        service,
        (sample_spec_file, sample_workdir),
        name="Corrupted Step Policy Loop",
        workflow=gatekeeper_workflow(),
        corruption=(("steps", 1, "action_policy", "workspace"), "workspace_write"),
    )

    assert run["status"] == "failed"
    assert "only Builder steps may set action_policy.workspace=workspace_write" in run["error_message"]
    assert not any(event["event_type"] == "role_execution_summary" and event["payload"].get("archetype") == "gatekeeper" for event in events)


def rerun_with_corrupted_workflow(
    service,
    samples: tuple[Path, Path],
    *,
    name: str,
    workflow: dict,
    corruption: tuple[tuple[object, ...], object],
) -> tuple[dict, list[dict]]:
    sample_spec_file, sample_workdir = samples
    loop = _create_loop(service, sample_spec_file, sample_workdir, name=name, workflow=workflow)
    corrupted_workflow = json.loads(json.dumps(loop["workflow_json"]))
    path, value = corruption
    set_nested(corrupted_workflow, path, value)
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(corrupted_workflow, ensure_ascii=False), loop["id"]),
        )
    run = service.rerun(loop["id"])
    return run, service.stream_events(run["id"], limit=100)


def set_nested(payload: dict, path: tuple[object, ...], value: object) -> None:
    current = payload
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def control_workflow() -> dict:
    workflow = gatekeeper_workflow()
    workflow["roles"].insert(1, role("guide", "guide"))
    workflow["controls"] = [
        {
            "id": "stale_evidence_check",
            "when": {"signal": "no_evidence_progress", "after": "0s"},
            "call": {"role_id": "guide"},
            "mode": "repair_guidance",
            "max_fires_per_run": 1,
        }
    ]
    return workflow


def gatekeeper_workflow(*, evidence_query: bool = False) -> dict:
    gatekeeper_step = {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"}
    if evidence_query:
        gatekeeper_step["inputs"] = {"evidence_query": {"archetypes": ["builder"], "limit": 12}}
    return {
        "version": 1,
        "roles": [role("builder", "builder"), role("gatekeeper", "gatekeeper")],
        "steps": [{"id": "builder_step", "role_id": "builder"}, gatekeeper_step],
    }


def role(role_id: str, archetype: str) -> dict:
    return {"id": role_id, "name": role_id.title(), "archetype": archetype, "prompt_ref": f"{archetype}.md"}
