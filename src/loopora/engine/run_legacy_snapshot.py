from __future__ import annotations

from loopora.events.replay import RunSnapshot
from loopora.kernel.run_state import RunState
from loopora.run_projection_fields import lifecycle_status_from_public_run_status
from loopora.utils import coerced_non_negative_int
from loopora.task_verdict_aliases import verdict_status_from_task_status


def legacy_run_snapshot(run_id: str, run: dict) -> RunSnapshot:
    return RunSnapshot(
        state=RunState(
            id=run_id,
            loop_id=str(run.get("loop_id") or ""),
            lifecycle_status=lifecycle_status_from_public_run_status(run.get("status")),
            current_iteration=coerced_non_negative_int(run.get("current_iter")),
            current_step_id=None,
            pending_actor=None,
            stop_requested=bool(run.get("stop_requested")),
        ),
        latest_event_sequence=0,
        verdict_status=verdict_status_from_task_status(run.get("task_verdict")),
    )


def missing_run_snapshot(run_id: str) -> RunSnapshot:
    return RunSnapshot(state=RunState(id=run_id, loop_id=""), latest_event_sequence=0)
