from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from loopora.diagnostics import get_logger, log_event
from loopora.executor_types import ExecutionStopped
from loopora.recovery import RetryConfig, execute_with_recovery
from loopora.service_types import RoleExecutionError
from loopora.utils import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True)
class RoleExecutionRequest:
    run_id: str
    iter_id: int | None
    role: str
    fn: Callable[[], dict]
    retry_config: RetryConfig
    degrade_once: Callable[[], None] | None = None
    event_context: Mapping[str, object] | None = None


class ServiceRoleExecutionLifecycleMixin:
    def _pause_between_iterations(self, run_id: str, duration_seconds: float, iter_id: int) -> None:
        if duration_seconds <= 0:
            return
        log_event(
            logger,
            logging.INFO,
            "service.run.iteration_wait.started",
            "Starting the configured wait between iterations",
            run_id=run_id,
            iter=iter_id,
            duration_seconds=duration_seconds,
        )
        self.append_run_event(
            run_id,
            "iteration_wait_started",
            {"iter": iter_id, "duration_seconds": duration_seconds},
        )
        deadline = time.monotonic() + duration_seconds
        while True:
            self._ensure_not_stopped(run_id)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(max(self.settings.polling_interval_seconds, 0.05), remaining))
        self.append_run_event(
            run_id,
            "iteration_wait_finished",
            {"iter": iter_id, "duration_seconds": duration_seconds},
        )
        log_event(
            logger,
            logging.INFO,
            "service.run.iteration_wait.finished",
            "Finished the configured wait between iterations",
            run_id=run_id,
            iter=iter_id,
            duration_seconds=duration_seconds,
        )

    def _wait_for_slot(self, run_id: str) -> None:
        self.repository.update_run(run_id, status="queued", summary_md="# Loopora Run Summary\n\nQueued.\n")
        waiting_started_at = time.perf_counter()
        waiting_logged = False
        while True:
            self._ensure_not_stopped(run_id)
            if self.repository.claim_run_slot(run_id, self.settings.max_concurrent_runs):
                self.repository.update_run(run_id, started_at=utc_now(), status="running")
                log_event(
                    logger,
                    logging.INFO,
                    "service.run.slot.acquired",
                    "Acquired a run slot and started execution",
                    run_id=run_id,
                    wait_duration_ms=int((time.perf_counter() - waiting_started_at) * 1000),
                    max_concurrent_runs=self.settings.max_concurrent_runs,
                )
                return
            if not waiting_logged:
                waiting_logged = True
                log_event(
                    logger,
                    logging.INFO,
                    "service.run.slot.waiting",
                    "Run is waiting for a free slot or workdir lock",
                    run_id=run_id,
                    polling_interval_seconds=self.settings.polling_interval_seconds,
                    max_concurrent_runs=self.settings.max_concurrent_runs,
                )
            time.sleep(self.settings.polling_interval_seconds)

    def _execute_role(
        self,
        request: RoleExecutionRequest,
    ) -> dict:
        started_at = time.perf_counter()
        log_context = {"run_id": request.run_id, "role": request.role}
        if request.iter_id is not None:
            log_context["iter"] = request.iter_id
        context_payload = dict(request.event_context or {})
        log_event(
            logger,
            logging.INFO,
            "service.role.execution.started",
            "Starting role execution",
            **log_context,
        )

        def wrapped() -> dict:
            self._ensure_not_stopped(request.run_id)
            self.repository.update_run(request.run_id, active_role=request.role)
            start_payload = {"role": request.role, **context_payload}
            if request.iter_id is not None:
                start_payload["iter"] = request.iter_id
            self.append_run_event(request.run_id, "role_started", start_payload, role=request.role)
            return request.fn()

        value, result = execute_with_recovery(wrapped, request.retry_config, degrade_once=request.degrade_once)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        summary_payload = {
            "role": request.role,
            **context_payload,
            "ok": result.ok,
            "attempts": result.attempts,
            "degraded": result.degraded,
            "error": str(result.error) if result.error else None,
            "duration_ms": duration_ms,
        }
        if request.iter_id is not None:
            summary_payload["iter"] = request.iter_id
        self.append_run_event(
            request.run_id,
            "role_execution_summary",
            summary_payload,
            role=request.role,
        )
        log_event(
            logger,
            logging.INFO if result.ok else logging.ERROR,
            "service.role.execution.completed",
            "Role execution finished",
            run_id=request.run_id,
            **summary_payload,
        )
        if not result.ok:
            raise RoleExecutionError(request.role, result)
        return value or {}

    def _ensure_not_stopped(self, run_id: str) -> None:
        if self.repository.should_stop(run_id):
            raise ExecutionStopped(f"run {run_id} was stopped")

    def _set_mode(self, run_id: str, iter_id: int, role: str, holder: dict[str, str], mode: str) -> None:
        holder["value"] = mode
        self.append_run_event(run_id, "role_degraded", {"iter": iter_id, "role": role, "mode": mode}, role=role)
        log_event(
            logger,
            logging.WARNING,
            "service.role.execution.degraded",
            "Role execution switched to a degraded mode after retries",
            run_id=run_id,
            iter=iter_id,
            role=role,
            mode=mode,
        )
