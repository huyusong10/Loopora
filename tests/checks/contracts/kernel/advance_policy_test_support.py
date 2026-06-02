from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext
from loopora.kernel import ActorRef


class RecordingRunnerCursor:
    def __init__(self, step_index: int) -> None:
        self.step_index = step_index
        self.request: dict[str, Any] | None = None

    def runner_step_index(self, run_id: str, **kwargs: Any) -> int:
        self.request = {"run_id": run_id, **kwargs}
        return self.step_index


def runner_actor() -> ActorRef:
    return ActorRef(kind="runner", id="headless")


def runner_iteration_state() -> RunnerIterationState:
    return RunnerIterationState(
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


def runner_run_context(
    tmp_path,
    *,
    run_id: str,
    strategy_steps: list[dict[str, Any]] | None = None,
) -> RunnerRunContext:
    return RunnerRunContext(
        run_id=run_id,
        run={"id": run_id},
        run_dir=tmp_path,
        strategy_source={},
        executor=object(),
        compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
        retry_config=object(),
        prompt_files={},
        layout=SimpleNamespace(run_contract_path=tmp_path / "run_contract.json"),
        run_contract={},
        strategy_steps=strategy_steps or [_step("builder", "builder"), _step("gatekeeper", "gatekeeper")],
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


def _step(step_id: str, role_id: str, **overrides: Any) -> dict[str, Any]:
    step = {"id": step_id, "role_id": role_id}
    step.update(overrides)
    return step
