from __future__ import annotations

from loopora.cli_agent_step_results import _attach_agent_run_summary
from loopora.run_projection_fields import projection_first_run_record_fields, run_status_from_run, task_verdict_from_run


def _event_projection_bundle() -> dict:
    return {
        "run_snapshot": {
            "schema_version": 1,
            "kind": "event_replayed_run_snapshot",
            "source_sequence": 12,
            "run_id": "run_projection_first",
            "loop_id": "loop_event",
            "lifecycle_status": "closed",
            "current_iteration": 2,
        },
        "task_verdict": {
            "schema_version": 1,
            "kind": "event_replayed_task_verdict",
            "source_sequence": 12,
            "status": "continue_required",
            "source": "system",
            "summary": "Projection still needs proof.",
        },
    }


def test_run_record_hydration_uses_event_projection_to_fill_missing_verdict() -> None:
    run = {
        "id": "run_projection_first",
        "status": "failed",
        "run_status": "failed",
    }

    run.update(projection_first_run_record_fields(_event_projection_bundle(), run=run))

    assert run_status_from_run(run) == "succeeded"
    assert task_verdict_from_run(run)["status"] == "insufficient_evidence"
    assert task_verdict_from_run(run)["source"] == "run_status"
    assert task_verdict_from_run(run)["summary"] == "Projection still needs proof."


def test_run_record_hydration_ignores_stale_projection_schema() -> None:
    projections = _event_projection_bundle()
    projections["run_snapshot"] = {**projections["run_snapshot"], "schema_version": 0}
    projections["task_verdict"] = {**projections["task_verdict"], "schema_version": 0}
    run = {
        "id": "run_projection_first",
        "status": "failed",
        "run_status": "failed",
    }

    run.update(projection_first_run_record_fields(projections, run=run))

    assert run_status_from_run(run) == "failed"
    assert task_verdict_from_run(run) == {}


def test_agent_run_summary_keeps_record_verdict_when_projection_cache_disagrees() -> None:
    result = {
        "adapter": "codex",
        "run": {
            "id": "run_projection_first",
            "status": "failed",
            "run_status": "failed",
            "workdir": "/workspace",
            "task_verdict_json": {"status": "failed", "source": "gatekeeper", "summary": "Record verdict wins."},
            "event_projections": _event_projection_bundle(),
        },
        "complete": True,
    }

    _attach_agent_run_summary(result)

    summary = result["agent_run_summary"]
    assert summary["run_status"] == "succeeded"
    assert summary["task_verdict_status"] == "failed"
    assert summary["task_verdict_summary"] == "Record verdict wins."
    assert summary["agent_work_panel"]["task_proven"] is False
