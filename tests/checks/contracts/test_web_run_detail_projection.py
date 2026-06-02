from __future__ import annotations

from loopora.web_projection import (
    web_run_detail_progress_stages,
    web_run_detail_projection,
)


LEGACY_CURRENT_ITERATION = 2
PROJECTED_CURRENT_ITERATION = 3
PROJECTED_SOURCE_SEQUENCE = 9


def test_run_detail_progress_projection_keeps_run_closure_language_neutral() -> None:
    stages = web_run_detail_progress_stages({"workflow_json": {"roles": [], "steps": []}})

    assert stages[-1] == {"key": "finished", "label": "Run closed", "kind": "finished", "sequence": 2}
    assert all(stage["label"] != "Done" for stage in stages)


def test_run_detail_progress_projection_prefers_strategy_source() -> None:
    stages = web_run_detail_progress_stages(
        {
            "strategy_source": {
                "roles": [{"id": "builder", "archetype": "builder", "name": "Builder"}],
                "steps": [{"id": "builder_step", "role_id": "builder"}],
            },
            "workflow_json": {"roles": [], "steps": []},
        }
    )

    assert stages[1] == {"key": "step:builder_step", "label": "Builder", "kind": "strategy_step", "sequence": 2}


def test_web_run_detail_core_state_prefers_event_projection_bundle_over_legacy_run_record() -> None:
    projection = web_run_detail_projection(
        {
            "id": "run_projection_first",
            "loop_id": "loop_legacy",
            "status": "failed",
            "run_status": "failed",
            "current_iter": 0,
            "active_role": "legacy-role",
        },
        event_projections={
            "run_snapshot": {
                "schema_version": 1,
                "kind": "event_replayed_run_snapshot",
                "source_sequence": PROJECTED_SOURCE_SEQUENCE,
                "run_id": "run_projection_first",
                "loop_id": "loop_from_events",
                "lifecycle_status": "closed",
                "current_iteration": PROJECTED_CURRENT_ITERATION,
                "current_step_id": None,
                "pending_actor": None,
                "verdict_status": "passed",
            },
            "task_verdict": {
                "schema_version": 1,
                "kind": "event_replayed_task_verdict",
                "source_sequence": PROJECTED_SOURCE_SEQUENCE,
                "status": "passed",
                "source": "gatekeeper",
                "summary": "Projection verdict wins.",
            },
        },
    )

    assert projection["summary"]["loop_id"] == "loop_from_events"
    assert projection["summary"]["run_status"] == "succeeded"
    assert projection["summary"]["current_iter"] == PROJECTED_CURRENT_ITERATION
    assert projection["lifecycle"]["run_status"] == "succeeded"
    assert projection["task_verdict"]["status"] == "passed"
    assert projection["diagnostics"]["source_shape"] == "projection_bundle"
    assert projection["diagnostics"]["projection_source_sequence"] == PROJECTED_SOURCE_SEQUENCE


def test_web_run_detail_preserves_legacy_numeric_compatibility_without_negative_progress() -> None:
    projection = web_run_detail_projection(
        {
            "id": "run_legacy_numeric",
            "loop_id": "loop_legacy",
            "status": "running",
            "current_iter": str(LEGACY_CURRENT_ITERATION),
            "active_role": "builder",
        }
    )

    assert projection["summary"]["current_iter"] == LEGACY_CURRENT_ITERATION
    assert projection["lifecycle"]["current_iter"] == LEGACY_CURRENT_ITERATION

    invalid_projection = web_run_detail_projection(
        {
            "id": "run_invalid_numeric",
            "loop_id": "loop_legacy",
            "status": "running",
            "current_iter": -1,
        },
        event_projections={
            "run_snapshot": {
                "schema_version": 1,
                "kind": "event_replayed_run_snapshot",
                "source_sequence": "-4",
                "run_id": "run_invalid_numeric",
                "loop_id": "loop_event",
                "lifecycle_status": "running",
                "current_iteration": -3,
            },
        },
    )

    assert invalid_projection["summary"]["current_iter"] is None
    assert invalid_projection["lifecycle"]["current_iter"] is None
    assert invalid_projection["diagnostics"]["projection_source_sequence"] is None
