from __future__ import annotations

from loopora.service_alignment_execution import (
    AlignmentExecutionState,
    AlignmentSessionTransitionPlan,
    alignment_bundle_candidate_outcome,
    alignment_bundle_ready_transition_plan,
    alignment_bundle_repair_transition_plan,
    alignment_waiting_user_transition_plan,
)


def test_alignment_waiting_user_transition_plan_projects_terminal_dialogue_state() -> None:
    assert alignment_waiting_user_transition_plan() == AlignmentSessionTransitionPlan(
        action="waiting_user",
        update_fields={"status": "waiting_user", "error_message": ""},
        event_type="alignment_waiting_user",
        event_payload={"status": "waiting_user"},
        finish_session=True,
        clear_active_child_pid=True,
    )


def test_alignment_bundle_transition_plans_project_ready_and_repair_state() -> None:
    ready = alignment_bundle_ready_transition_plan(bundle_path="/tmp/alignment/bundle.yaml")

    assert ready == AlignmentSessionTransitionPlan(
        action="ready",
        update_fields={"status": "ready", "alignment_stage": "ready", "error_message": ""},
        event_type="alignment_ready",
        event_payload={"status": "ready", "bundle_path": "/tmp/alignment/bundle.yaml"},
        finish_session=True,
        clear_active_child_pid=True,
    )

    repair = alignment_bundle_candidate_outcome(
        ok=False,
        error="bundle is invalid",
        repair_attempts=0,
        bundle_yaml="version: 1\n",
    )

    assert alignment_bundle_repair_transition_plan(repair) == AlignmentSessionTransitionPlan(
        action="repair",
        update_fields={"status": "repairing", "repair_attempts": 1, "error_message": "bundle is invalid"},
        event_type="alignment_repair_started",
        event_payload={"status": "repairing", "error": "bundle is invalid"},
    )
    assert repair.next_state == AlignmentExecutionState(
        mode="repair",
        validation_error="bundle is invalid",
        invalid_yaml="version: 1\n",
    )
