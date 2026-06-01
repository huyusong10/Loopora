from __future__ import annotations

from types import SimpleNamespace

from loopora.engine import (
    RunnerStepCursorFromEventsRequest,
    RunnerStepSelectionRequest,
    select_next_runner_step,
    runner_step_index_from_events,
)
from loopora.engine.runner_context import (
    RunnerIterationState,
    RunnerRunContext,
    runner_parallel_group_claim_plan,
    runner_step_claim_plan,
)
from loopora.kernel import ActorRef


def test_advance_policy_selects_strategy_step_by_cursor() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            step_index=1,
        )
    )

    assert selection is not None
    assert selection.step_order == 1
    assert selection.step["id"] == "gatekeeper"


def test_advance_policy_returns_none_after_strategy_steps_are_exhausted() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[{"id": "builder", "role_id": "builder"}],
            step_index=1,
        )
    )

    assert selection is None


def test_advance_policy_rejects_bool_cursor_values() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            step_index=True,
        )
    )
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[{"id": "builder", "role_id": "builder"}],
            events=[],
            iteration=0,
            fallback_step_index=True,
        )
    )

    assert selection is not None
    assert selection.step_order == 0
    assert selection.step["id"] == "builder"
    assert step_index == 0


def test_advance_policy_preserves_parallel_group_signal() -> None:
    selection = select_next_runner_step(
        RunnerStepSelectionRequest(
            strategy_steps=[{"id": "inspect_a", "role_id": "inspector", "parallel_group": "review"}],
            step_index=0,
        )
    )

    assert selection is not None
    assert selection.parallel_group == "review"


def test_advance_policy_derives_cursor_from_committed_step_events() -> None:
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            events=[SimpleNamespace(event_type="StepCommitted", payload={"step_id": "builder", "iteration": 0})],
            iteration=0,
            fallback_step_index=0,
        )
    )

    assert step_index == 1


def test_advance_policy_prefers_claimable_current_step_projection() -> None:
    step_index = runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            events=[SimpleNamespace(event_type="StepCommitted", payload={"step_id": "builder", "iteration": 0})],
            iteration=0,
            fallback_step_index=0,
            current_step_projection={
                "source_sequence": 4,
                "claimable": True,
                "step_id": "gatekeeper",
                "iteration": 0,
            },
        )
    )

    assert step_index == 1


def test_runner_step_claim_plan_uses_run_engine_cursor_and_freezes_instruction(tmp_path) -> None:
    class RecordingRunnerCursor:
        request: dict | None = None

        def runner_step_index(self, run_id: str, **kwargs) -> int:
            self.request = {"run_id": run_id, **kwargs}
            return 1

    cursor = RecordingRunnerCursor()
    actor = ActorRef(kind="runner", id="headless")

    plan = runner_step_claim_plan(
        cursor,
        RunnerRunContext(
            run_id="run_claim_plan",
            run={"id": "run_claim_plan"},
            run_dir=tmp_path,
            strategy_source={},
            executor=object(),
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            retry_config=object(),
            prompt_files={},
            layout=SimpleNamespace(run_contract_path=tmp_path / "run_contract.json"),
            run_contract={},
            strategy_steps=[
                {"id": "builder", "role_id": "builder"},
                {"id": "gatekeeper", "role_id": "gatekeeper"},
            ],
            strategy_controls=[],
            control_fire_counts={},
            runner_started_at=0,
            role_by_id={
                "builder": {"id": "builder", "name": "Builder", "archetype": "builder"},
                "gatekeeper": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            },
            completion_mode="gatekeeper",
        ),
        RunnerIterationState(
            iter_id=0,
            previous_composite=None,
            stagnation={},
            previous_outputs_by_step={},
            previous_outputs_by_role={},
            previous_outputs_by_archetype={},
            previous_handoffs_by_step={},
            previous_handoffs_by_role={},
            previous_iteration_summary=None,
            previous_session_refs_by_step={},
        ),
        pending_actor=actor,
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
    class RecordingRunnerCursor:
        def runner_step_index(self, _run_id: str, **_kwargs) -> int:
            return 1

    actor = ActorRef(kind="runner", id="headless")
    context = RunnerRunContext(
        run_id="run_parallel_claim_plan",
        run={"id": "run_parallel_claim_plan"},
        run_dir=tmp_path,
        strategy_source={},
        executor=object(),
        compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
        retry_config=object(),
        prompt_files={},
        layout=SimpleNamespace(run_contract_path=tmp_path / "run_contract.json"),
        run_contract={},
        strategy_steps=[
            {"id": "builder", "role_id": "builder"},
            {"id": "inspect_a", "role_id": "inspector", "parallel_group": "review"},
            {"id": "inspect_b", "role_id": "inspector", "parallel_group": "review"},
            {"id": "gatekeeper", "role_id": "gatekeeper"},
        ],
        strategy_controls=[],
        control_fire_counts={},
        runner_started_at=0,
        role_by_id={
            "builder": {"id": "builder", "name": "Builder", "archetype": "builder"},
            "inspector": {"id": "inspector", "name": "Inspector", "archetype": "inspector"},
            "gatekeeper": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        },
        completion_mode="gatekeeper",
    )
    iteration = RunnerIterationState(
        iter_id=0,
        previous_composite=None,
        stagnation={},
        previous_outputs_by_step={},
        previous_outputs_by_role={},
        previous_outputs_by_archetype={},
        previous_handoffs_by_step={},
        previous_handoffs_by_role={},
        previous_iteration_summary=None,
        previous_session_refs_by_step={},
    )
    first_plan = runner_step_claim_plan(
        RecordingRunnerCursor(),
        context,
        iteration,
        pending_actor=actor,
    )

    assert first_plan is not None
    group_plan = runner_parallel_group_claim_plan(
        context,
        iteration,
        first_plan=first_plan,
        pending_actor=actor,
    )

    assert group_plan.parallel_group == "review"
    assert group_plan.group_start == 1
    assert group_plan.next_step_index == 3
    assert [plan.step_order for plan in group_plan.steps] == [1, 2]
    assert [plan.claim_request.instruction.step_id for plan in group_plan.steps] == ["inspect_a", "inspect_b"]
    assert all(plan.claim_request.instruction.action_policy.can_spawn_parallel for plan in group_plan.steps)
