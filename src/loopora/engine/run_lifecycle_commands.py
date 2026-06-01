from __future__ import annotations

from loopora.engine.run_lifecycle import (
    RunEngineAdvanceOutcome,
    RunEngineAdvanceStatus,
    advance_outcome,
    advance_outcome_for_snapshot,
)
from loopora.engine.run_legacy_updates import mark_run_started, mark_run_succeeded
from loopora.engine.run_requests import RunEngineFailRunRequest, RunEngineStopRunRequest
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.events.append_requests import RunEventAppend
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache
from loopora.kernel.run_state import RunLifecycleStatus
from loopora.kernel.verdict import VerdictStatus


def start_run(repository, run_id: str) -> RunEngineAdvanceOutcome:
    snapshot = run_snapshot_from_repository(repository, run_id)
    if not snapshot.state.loop_id:
        return advance_outcome(snapshot, RunEngineAdvanceStatus.MISSING, next_action="missing")
    if snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED:
        mark_run_started(repository, run_id)
        snapshot = run_snapshot_from_repository(repository, run_id)
    return advance_outcome_for_snapshot(snapshot)


def advance_run(repository, run_id: str) -> RunEngineAdvanceOutcome:
    snapshot = run_snapshot_from_repository(repository, run_id)
    if not snapshot.state.loop_id:
        return advance_outcome(snapshot, RunEngineAdvanceStatus.MISSING, next_action="missing")
    if snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED:
        return start_run(repository, run_id)
    if snapshot.state.lifecycle_status in {RunLifecycleStatus.CLOSED, RunLifecycleStatus.STOPPED, RunLifecycleStatus.FAILED}:
        return advance_outcome_for_snapshot(snapshot)
    if snapshot.verdict_status in {VerdictStatus.PASSED, VerdictStatus.PASSED_WITH_RESIDUAL_RISK}:
        mark_run_succeeded(repository, run_id)
        return advance_outcome_for_snapshot(run_snapshot_from_repository(repository, run_id))
    return advance_outcome_for_snapshot(snapshot)


def stop_run(repository, request: RunEngineStopRunRequest) -> RunEngineAdvanceOutcome:
    return _append_non_success_terminal_event(
        repository,
        request,
        event_type="RunStopped",
    )


def fail_run(repository, request: RunEngineFailRunRequest) -> RunEngineAdvanceOutcome:
    return _append_non_success_terminal_event(
        repository,
        request,
        event_type="RunFailed",
    )


def _append_non_success_terminal_event(
    repository,
    request: RunEngineStopRunRequest | RunEngineFailRunRequest,
    *,
    event_type: str,
) -> RunEngineAdvanceOutcome:
    run_id = request.run_id
    snapshot = run_snapshot_from_repository(repository, run_id)
    if not snapshot.state.loop_id:
        return advance_outcome(snapshot, RunEngineAdvanceStatus.MISSING, next_action="missing")
    if snapshot.state.lifecycle_status in {RunLifecycleStatus.CLOSED, RunLifecycleStatus.STOPPED, RunLifecycleStatus.FAILED}:
        return advance_outcome_for_snapshot(snapshot)
    append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=run_id,
            event_type=event_type,
            actor=request.actor,
            payload={"run_id": run_id, "reason": request.reason},
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )
    return advance_outcome_for_snapshot(run_snapshot_from_repository(repository, run_id))
