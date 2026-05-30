from __future__ import annotations

from loopora.engine.advance_policy import RunnerStepCursorFromEventsRequest, runner_step_index_from_events
from loopora.events.projection_cache import current_step_projection_for_run
from loopora.events.run_event_queries import list_run_events


def runner_step_index_for_run(
    repository,
    run_id: str,
    *,
    strategy_steps: list[dict],
    iteration: int,
    fallback_step_index: int = 0,
) -> int:
    return runner_step_index_from_events(
        RunnerStepCursorFromEventsRequest(
            strategy_steps=strategy_steps,
            events=list_run_events(repository, run_id),
            iteration=iteration,
            fallback_step_index=fallback_step_index,
            current_step_projection=current_step_projection_for_run(repository, run_id),
        )
    )
