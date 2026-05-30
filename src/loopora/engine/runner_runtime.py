from __future__ import annotations

from dataclasses import dataclass, field

from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext


@dataclass
class RunnerRunProgress:
    stagnation: dict
    last_iter_id: int = -1
    last_step_results: list[dict] = field(default_factory=list)
    previous_outputs_by_step: dict[str, dict] = field(default_factory=dict)
    previous_outputs_by_role: dict[str, dict] = field(default_factory=dict)
    previous_outputs_by_archetype: dict[str, dict] = field(default_factory=dict)
    previous_handoffs_by_step: dict[str, dict] = field(default_factory=dict)
    previous_handoffs_by_role: dict[str, dict] = field(default_factory=dict)
    previous_iteration_summary: dict | None = None
    previous_session_refs_by_step: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class RunnerStepRunRequest:
    context: RunnerRunContext
    iteration: RunnerIterationState
    step_order: int
    step: dict
    state_snapshot: dict[str, object]
    is_control: bool = False
