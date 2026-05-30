from __future__ import annotations

from loopora.engine.run_legacy_snapshot import legacy_run_snapshot, missing_run_snapshot
from loopora.events.projection_cache import run_snapshot_projection_for_run
from loopora.events.replay import RunSnapshot
from loopora.projections.run_snapshot import run_snapshot_from_projection


def run_snapshot_from_repository(repository, run_id: str) -> RunSnapshot:
    cached_snapshot = run_snapshot_from_projection(run_snapshot_projection_for_run(repository, run_id))
    if cached_snapshot is not None and cached_snapshot.state.id == run_id and cached_snapshot.latest_event_sequence > 0:
        return cached_snapshot
    run = repository.get_run(run_id)
    if not run:
        return missing_run_snapshot(run_id)
    return legacy_run_snapshot(run_id, run)
