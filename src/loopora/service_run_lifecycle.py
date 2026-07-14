from __future__ import annotations

import logging
import threading
from pathlib import Path

from loopora.diagnostics import get_logger, log_event, log_exception
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR, background_worker_start_failure_summary
from loopora.run_observation_events import TAKEAWAY_PROJECTION_EVENT_TYPES
from loopora.service_loop_deletion import ServiceLoopDeletionMixin
from loopora.service_run_acceptance import ServiceRunAcceptanceMixin
from loopora.service_run_continuation import ServiceRunContinuationMixin
from loopora.service_run_evidence_export import ServiceRunEvidenceExportMixin
from loopora.service_run_file_access import ServiceRunFileAccessMixin
from loopora.service_run_finalization import TerminalRunFinalizationRequest
from loopora.service_run_observation import ServiceRunObservationMixin
from loopora.service_run_recovery import ServiceRunRecoveryMixin
from loopora.service_run_takeaway_projection import ServiceRunTakeawayProjectionMixin
from loopora.service_types import (
    ACTIVE_RUN_STATUSES,
    LooporaConflictError,
    LooporaError,
    LooporaNotFoundError,
    TERMINAL_RUN_STATUSES,
)

logger = get_logger(__name__)


class ServiceRunLifecycleMixin(
    ServiceRunTakeawayProjectionMixin,
    ServiceRunAcceptanceMixin,
    ServiceRunContinuationMixin,
    ServiceRunEvidenceExportMixin,
    ServiceRunFileAccessMixin,
    ServiceLoopDeletionMixin,
    ServiceRunRecoveryMixin,
    ServiceRunObservationMixin,
):
    def append_run_event(self, run_id: str, event_type: str, payload: dict, role: str | None = None) -> dict:
        event = self.repository.append_event(run_id, event_type, payload, role=role)
        if event_type in TAKEAWAY_PROJECTION_EVENT_TYPES:
            self._record_run_takeaway_projection_for_event(run_id, int(event.get("id") or 0))
        return event

    def _reap_terminal_thread_handle(self, run_id: object, *, status: object) -> None:
        normalized_run_id = str(run_id or "").strip()
        normalized_status = str(status or "").strip()
        if not normalized_run_id or normalized_status not in TERMINAL_RUN_STATUSES:
            return
        thread = self._threads.get(normalized_run_id)
        if thread is None:
            return
        if thread.ident == threading.get_ident():
            return
        if thread.is_alive():
            thread.join(timeout=0.1)
        if not thread.is_alive():
            self._threads.pop(normalized_run_id, None)

    def start_run_async(self, run_id: str) -> None:
        existing = self._threads.get(run_id)
        if existing is not None:
            if existing.is_alive():
                raise LooporaConflictError(f"run {run_id} is already executing in this process")
            self._threads.pop(run_id, None)
        if not self._try_mark_run_active(run_id):
            raise LooporaConflictError(f"run {run_id} is already executing in this process")
        thread = self._build_run_thread(run_id)
        self._threads[run_id] = thread
        try:
            thread.start()
            log_event(
                logger,
                logging.INFO,
                "service.run.dispatched",
                "Dispatched run to a background thread",
                run_id=run_id,
                thread_name=thread.name,
            )
        except Exception as exc:
            self._mark_run_inactive(run_id)
            self._threads.pop(run_id, None)
            self._fail_run_after_worker_start_error(run_id, exc)
            raise LooporaError(BACKGROUND_WORKER_START_ERROR) from exc

    def _fail_run_after_worker_start_error(self, run_id: str, exc: BaseException) -> None:
        run = self.repository.get_run(run_id)
        log_exception(
            logger,
            "service.run.dispatch_failed",
            "Failed to start run background worker",
            error=exc,
            **self._run_log_context(run),
        )
        if not run:
            return
        try:
            failed = self._finalize_terminal_run(
                TerminalRunFinalizationRequest(
                    run_id=run_id,
                    run_dir=Path(run["runs_dir"]),
                    status="failed",
                    summary=background_worker_start_failure_summary(),
                    error_message=BACKGROUND_WORKER_START_ERROR,
                    final_reason="background_worker_start_failed",
                )
            )
            self._append_run_aborted_event(
                run_id,
                role=None,
                attempts=1,
                degraded=False,
                error_text=BACKGROUND_WORKER_START_ERROR,
            )
            self.append_run_event(
                run_id,
                "run_finished",
                self._run_finished_event_payload(failed, status="failed", reason="background_worker_start_failed"),
            )
        except Exception as finalization_exc:  # noqa: BLE001 - dispatch failure must still surface a stable error.
            log_exception(
                logger,
                "service.run.dispatch_failure_finalization_failed",
                "Failed to persist run dispatch failure",
                error=finalization_exc,
                **self._run_log_context(run),
            )

    def _build_run_thread(self, run_id: str) -> threading.Thread:
        return threading.Thread(
            target=self._execute_preclaimed_run,
            args=(run_id,),
            daemon=True,
            name=f"run-{run_id}",
        )

    def stop_run(self, run_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        current = self.repository.get_run(run_id)
        if not current:
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        if current["status"] not in ACTIVE_RUN_STATUSES:
            raise LooporaConflictError(f"cannot stop run in status {current['status']}")

        run = self.repository.request_stop(run_id)
        if not run:
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        self.append_run_event(run_id, "stop_requested", {"status": run["status"]})
        if str(run.get("status") or "") == "queued" and not self._is_run_active_locally(run_id):
            summary = "# Loopora Run Summary\n\nStopped before a worker claimed this queued run.\n"
            stopped = self._finalize_terminal_run(
                TerminalRunFinalizationRequest(
                    run_id=run_id,
                    run_dir=Path(run["runs_dir"]),
                    status="stopped",
                    summary=summary,
                    final_reason="stopped",
                    hydrate=True,
                )
            )
            self.repository.release_run_slot(run_id)
            self.append_run_event(
                run_id,
                "run_finished",
                self._run_finished_event_payload(stopped, status="stopped", reason="stopped_before_start"),
            )
            return stopped
        if str(run.get("status") or "") == "awaiting_agent":
            summary = "# Loopora Run Summary\n\nStopped while waiting for host Agent step submission.\n"
            stopped = self._finalize_terminal_run(
                TerminalRunFinalizationRequest(
                    run_id=run_id,
                    run_dir=Path(run["runs_dir"]),
                    status="stopped",
                    summary=summary,
                    final_reason="stopped",
                    hydrate=True,
                )
            )
            self.repository.release_run_slot(run_id)
            self.append_run_event(run_id, "run_finished", self._run_finished_event_payload(stopped, status="stopped"))
            return stopped
        self.repository.send_stop_signal(run_id)
        log_event(
            logger,
            logging.INFO,
            "service.run.stop.requested",
            "Requested run stop",
            **self._run_log_context(run, status=run["status"]),
        )
        return run

    def rerun(self, loop_id: str, *, background: bool = False) -> dict:
        log_event(
            logger,
            logging.INFO,
            "service.run.rerun.requested",
            "Received rerun request for loop",
            loop_id=loop_id,
            background=background,
        )
        run = self.start_next_run(loop_id)
        if background:
            try:
                self.start_run_async(run["id"])
            except LooporaError as exc:
                if str(exc) != BACKGROUND_WORKER_START_ERROR:
                    raise
                return {**self.get_run(run["id"]), "run_start_error": str(exc)}
            return run
        return self.execute_run(run["id"])
