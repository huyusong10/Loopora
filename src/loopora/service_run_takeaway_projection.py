from __future__ import annotations

from loopora.diagnostics import get_logger, log_exception
from loopora.run_observation_events import TAKEAWAY_PROJECTION_EVENT_TYPES
from loopora.run_takeaways import build_minimal_run_takeaway_projection, build_run_key_takeaways

logger = get_logger(__name__)


class ServiceRunTakeawayProjectionMixin:
    def _record_run_takeaway_projection_for_event(self, run_id: str, source_event_id: int) -> None:
        if source_event_id <= 0:
            return
        try:
            run = self.repository.get_run(run_id)
            if not run:
                return
            payload = build_run_key_takeaways(self._hydrate_run_files(run))
            self.repository.record_run_takeaway_projection(run_id, source_event_id, payload)
        except Exception as exc:  # noqa: BLE001 - takeaway projection failures must not change run state.
            log_exception(
                logger,
                "service.run_takeaway_projection.write_failed",
                "Failed to persist run takeaway projection",
                error=exc,
                run_id=run_id,
                source_event_id=source_event_id,
            )

    def _backfill_missing_run_takeaway_projections(self) -> None:
        if not hasattr(self.repository, "list_terminal_runs_without_takeaway_projection"):
            return
        for run in self.repository.list_terminal_runs_without_takeaway_projection(limit=5000):
            run_id = str(run.get("id") or "").strip()
            if not run_id:
                continue
            try:
                trigger_event_id = self.repository.latest_event_id_for_types(
                    run_id,
                    TAKEAWAY_PROJECTION_EVENT_TYPES,
                )
                latest_event_id = self.repository.latest_event_id(run_id)
                source_event_id = trigger_event_id or latest_event_id
                if source_event_id <= 0:
                    continue
                hydrated = self._hydrate_run_files(run)
                payload = (
                    build_run_key_takeaways(hydrated) if trigger_event_id else build_minimal_run_takeaway_projection(hydrated, source_event_id=source_event_id)
                )
                self.repository.record_run_takeaway_projection(run_id, source_event_id, payload)
            except Exception as exc:  # noqa: BLE001 - projection backfill is best-effort startup repair.
                log_exception(
                    logger,
                    "service.run_takeaway_projection.backfill_failed",
                    "Failed to backfill run takeaway projection",
                    error=exc,
                    run_id=run_id,
                )
