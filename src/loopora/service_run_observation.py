from __future__ import annotations

from collections.abc import Iterable

from loopora.db_event_records import RunObservationSnapshotRowsRequest
from loopora.run_observation_events import PROGRESS_EVENT_TYPES, TIMELINE_EVENT_TYPES
from loopora.run_takeaways import build_minimal_run_takeaway_projection, normalize_run_takeaway_projection_shape
from loopora.service_run_current_step_projection import current_agent_step_projection
from loopora.service_types import LooporaNotFoundError
from loopora.settings import app_home
from loopora.structured_numbers import structured_non_negative_int


class ServiceRunObservationMixin:
    def recent_run_events(
        self,
        run_id: str,
        *,
        event_types: Iterable[str] | None = None,
        max_event_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.list_recent_events(
            run_id,
            event_types=event_types,
            max_event_id=max_event_id,
            limit=limit,
        )

    def latest_run_event_id(self, run_id: str) -> int:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.latest_event_id(run_id)

    def run_observation_snapshot(self, run_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        snapshot = self.repository.run_observation_snapshot_rows(
            RunObservationSnapshotRowsRequest(
                run_id=run_id,
                timeline_event_types=TIMELINE_EVENT_TYPES,
                progress_event_types=PROGRESS_EVENT_TYPES,
                timeline_limit=40,
                console_limit=160,
                progress_limit=2000,
            )
        )
        if snapshot is None:
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        run = self._hydrate_run_files(snapshot["run"])
        key_takeaways = snapshot.get("key_takeaway_projection")
        if not isinstance(key_takeaways, dict) or not key_takeaways:
            key_takeaways = build_minimal_run_takeaway_projection(run, source_event_id=snapshot["latest_event_id"])
        else:
            key_takeaways = normalize_run_takeaway_projection_shape(run, key_takeaways)
        key_takeaways["source_event_id"] = min(
            structured_non_negative_int(key_takeaways.get("source_event_id")),
            structured_non_negative_int(snapshot["latest_event_id"]),
        )
        current_agent_step = current_agent_step_projection(run)
        snapshot.pop("key_takeaway_projection", None)
        return {**snapshot, "run": run, "key_takeaways": key_takeaways, "current_agent_step": current_agent_step}

    def get_runtime_activity(self) -> dict:
        self._reconcile_local_orphaned_runs()
        active_runs = self.repository.list_active_runs()
        loop_name_by_id = {loop["id"]: loop["name"] for loop in self.repository.list_loops()}
        running_count = 0
        queued_count = 0
        awaiting_agent_count = 0
        runs = []
        for run in active_runs:
            status = str(run.get("status") or "").strip()
            if status == "running":
                running_count += 1
            elif status == "queued":
                queued_count += 1
            elif status == "awaiting_agent":
                awaiting_agent_count += 1
            runs.append(
                {
                    "id": run["id"],
                    "loop_id": run["loop_id"],
                    "loop_name": loop_name_by_id.get(run["loop_id"]) or run["loop_id"],
                    "status": status or "queued",
                    "active_role": run.get("active_role"),
                    "current_iter": run.get("current_iter"),
                    "workdir": run.get("workdir"),
                    "updated_at": run.get("updated_at"),
                }
            )
        return {
            "app_home": str(app_home().resolve()),
            "running_count": running_count,
            "queued_count": queued_count,
            "awaiting_agent_count": awaiting_agent_count,
            "has_running_runs": running_count > 0,
            "has_active_runs": bool(active_runs),
            "runs": runs,
        }

    def stream_events(self, run_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.list_events(run_id, after_id=after_id, limit=limit)
