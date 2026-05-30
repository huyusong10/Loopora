from __future__ import annotations

from loopora.events.run_event_payloads import iteration_completed_payload, iteration_started_payload
from loopora.engine.run_requests import RunEngineCompleteIterationRequest, RunEngineStartIterationRequest
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache
from loopora.events.run_event_queries import find_iteration_event


def append_iteration_start_and_rebuild_projection_cache(
    repository,
    request: RunEngineStartIterationRequest,
) -> EventEnvelope:
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=request.run_id,
            event_type="IterationStarted",
            actor=request.actor,
            payload=iteration_started_payload(
                run_id=request.run_id,
                iteration=request.iteration,
                step_count=request.step_count,
            ),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )


def append_iteration_start_if_absent_and_rebuild_projection_cache(
    repository,
    request: RunEngineStartIterationRequest,
) -> EventEnvelope:
    existing = find_iteration_event(repository, request.run_id, "IterationStarted", request.iteration)
    if existing is not None:
        return existing
    return append_iteration_start_and_rebuild_projection_cache(repository, request)


def append_iteration_completion_and_rebuild_projection_cache(
    repository,
    request: RunEngineCompleteIterationRequest,
) -> EventEnvelope:
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=request.run_id,
            event_type="IterationCompleted",
            actor=request.actor,
            payload=iteration_completed_payload(
                run_id=request.run_id,
                iteration=request.iteration,
                completed_step_count=request.completed_step_count,
                reason=request.reason,
            ),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )


def append_iteration_completion_if_absent_and_rebuild_projection_cache(
    repository,
    request: RunEngineCompleteIterationRequest,
) -> EventEnvelope:
    existing = find_iteration_event(repository, request.run_id, "IterationCompleted", request.iteration)
    if existing is not None:
        return existing
    return append_iteration_completion_and_rebuild_projection_cache(repository, request)
