from __future__ import annotations

from loopora.engine.advance_policy import WorkflowCursorFromEventsRequest, workflow_step_index_from_events
from loopora.events.streams import run_stream_id
from loopora.events.projection_cache import current_step_projection_for_run


def workflow_step_index_for_run(
    repository,
    run_id: str,
    *,
    workflow_steps: list[dict],
    iteration: int,
    fallback_step_index: int = 0,
) -> int:
    return workflow_step_index_from_events(
        WorkflowCursorFromEventsRequest(
            workflow_steps=workflow_steps,
            events=repository.list_domain_events(run_stream_id(run_id)),
            iteration=iteration,
            fallback_step_index=fallback_step_index,
            current_step_projection=current_step_projection_for_run(repository, run_id),
        )
    )
