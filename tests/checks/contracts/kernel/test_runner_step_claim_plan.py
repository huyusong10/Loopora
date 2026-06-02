from __future__ import annotations

from loopora.engine.runner_context import runner_parallel_group_claim_plan, runner_step_claim_plan

from advance_policy_test_support import (
    RecordingRunnerCursor,
    runner_actor,
    runner_iteration_state,
    runner_run_context,
)


NEXT_STEP_INDEX_AFTER_REVIEW_GROUP = 3


def test_runner_step_claim_plan_uses_run_engine_cursor_and_freezes_instruction(tmp_path) -> None:
    cursor = RecordingRunnerCursor(step_index=1)
    plan = runner_step_claim_plan(
        cursor,
        runner_run_context(tmp_path, run_id="run_claim_plan"),
        runner_iteration_state(),
        pending_actor=runner_actor(),
        fallback_step_index=0,
    )

    assert plan is not None
    assert cursor.request == {
        "run_id": "run_claim_plan",
        "strategy_steps": [
            {"id": "builder", "role_id": "builder"},
            {"id": "gatekeeper", "role_id": "gatekeeper"},
        ],
        "iteration": 0,
        "fallback_step_index": 0,
    }
    assert plan.step_order == 1
    assert plan.step["id"] == "gatekeeper"
    assert plan.claim_request.instruction.step_id == "gatekeeper"
    assert plan.claim_request.instruction.evidence_scope.target_ids == ("done_when.proof",)


def test_runner_parallel_group_claim_plan_freezes_peer_instructions(tmp_path) -> None:
    context = runner_run_context(
        tmp_path,
        run_id="run_parallel_claim_plan",
        strategy_steps=[
            {"id": "builder", "role_id": "builder"},
            {"id": "inspect_a", "role_id": "inspector", "parallel_group": "review"},
            {"id": "inspect_b", "role_id": "inspector", "parallel_group": "review"},
            {"id": "gatekeeper", "role_id": "gatekeeper"},
        ],
    )
    iteration = runner_iteration_state()
    first_plan = runner_step_claim_plan(
        RecordingRunnerCursor(step_index=1),
        context,
        iteration,
        pending_actor=runner_actor(),
    )

    assert first_plan is not None
    group_plan = runner_parallel_group_claim_plan(
        context,
        iteration,
        first_plan=first_plan,
        pending_actor=runner_actor(),
    )

    assert group_plan.parallel_group == "review"
    assert group_plan.group_start == 1
    assert group_plan.next_step_index == NEXT_STEP_INDEX_AFTER_REVIEW_GROUP
    assert [plan.step_order for plan in group_plan.steps] == [1, 2]
    assert [plan.claim_request.instruction.step_id for plan in group_plan.steps] == ["inspect_a", "inspect_b"]
    assert all(plan.claim_request.instruction.action_policy.can_spawn_parallel for plan in group_plan.steps)
