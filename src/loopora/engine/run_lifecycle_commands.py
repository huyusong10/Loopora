from __future__ import annotations

from loopora.engine.run_lifecycle import (
    RunEngineAdvanceOutcome,
    RunEngineAdvanceStatus,
    advance_outcome,
    advance_outcome_for_snapshot,
)
from loopora.engine.run_lifecycle_updates import mark_run_started, mark_run_succeeded
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
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
