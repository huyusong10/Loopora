from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path

from loopora.diagnostics import get_logger, log_event, log_exception
from loopora.service_run_finalization import TerminalRunFinalizationRequest

logger = get_logger(__name__)


class ServiceRunRecoveryMixin:
    def _reconcile_stale_runs(self) -> None:
        for run in self.repository.list_active_runs():
            if self._run_process_may_still_be_alive(run):
                continue
            if not self._startup_stale_run_is_recoverable(run):
                continue
            log_event(
                logger,
                logging.WARNING,
                "service.run.recovered_after_startup",
                "Recovered stale run during service startup",
                **self._run_log_context(run, runner_pid=run.get("runner_pid"), status=run.get("status")),
            )
            summary = "# Loopora Run Summary\n\nThis run was marked stopped when Loopora restarted because its previous worker process was no longer alive.\n"
            stopped = self._finalize_terminal_run(
                TerminalRunFinalizationRequest(
                    run_id=run["id"],
                    run_dir=Path(run["runs_dir"]),
                    status="stopped",
                    summary=summary,
                    error_message="Recovered stale run after service startup.",
                    final_reason="stale_worker_recovered",
                )
            )
            self.repository.release_run_slot(run["id"])
            self.append_run_event(
                run["id"],
                "run_finished",
                self._run_finished_event_payload(
                    stopped,
                    status="stopped",
                    reason="Recovered stale run after service startup.",
                ),
            )

    def _run_process_may_still_be_alive(self, run: dict) -> bool:
        pid = run.get("runner_pid")
        if run.get("status") == "queued":
            return bool(pid and self._pid_exists(pid))
        return bool(pid and self._pid_exists(pid))

    def _startup_stale_run_is_recoverable(self, run: dict) -> bool:
        if run.get("status") == "awaiting_agent":
            return False
        if run.get("runner_pid"):
            return True
        updated_at = self._parse_run_timestamp(run.get("updated_at") or run.get("started_at") or run.get("queued_at"))
        if updated_at is None:
            return False
        age_seconds = time.time() - updated_at.timestamp()
        return age_seconds >= self._local_run_orphan_grace_seconds()

    def _reconcile_local_orphaned_runs(self) -> None:
        for run in self.repository.list_active_runs():
            self._recover_local_orphaned_run(run)

    def _recover_local_orphaned_run(self, run: dict) -> dict:
        if not self._should_recover_local_orphan(run):
            return run

        reason = "Recovered orphaned run after the local worker stopped unexpectedly."
        log_event(
            logger,
            logging.WARNING,
            "service.run.recovered_orphan",
            "Recovered local orphaned run after the worker stopped unexpectedly",
            **self._run_log_context(
                run,
                status=run.get("status"),
                runner_pid=run.get("runner_pid"),
                child_pid=run.get("child_pid"),
                updated_at=run.get("updated_at"),
            ),
        )
        summary = "# Loopora Run Summary\n\nThis run was marked failed because the local worker stopped unexpectedly before it could finish cleanly.\n"
        child_pid = run.get("child_pid")
        if child_pid and self._pid_exists(child_pid):
            try:
                os.kill(int(child_pid), 15)
            except OSError:
                log_exception(
                    logger,
                    "service.run.orphan_child_stop_failed",
                    "Failed to stop orphaned child process",
                    run_id=run["id"],
                    loop_id=run.get("loop_id"),
                    workdir=run.get("workdir"),
                    child_pid=child_pid,
                )
        updated = self._finalize_terminal_run(
            TerminalRunFinalizationRequest(
                run_id=run["id"],
                run_dir=Path(run["runs_dir"]),
                status="failed",
                summary=summary,
                error_message=reason,
                final_reason="orphaned_worker",
            )
        )
        self.repository.release_run_slot(run["id"])
        self._append_run_aborted_event(
            run["id"],
            role=run.get("active_role"),
            attempts=1,
            degraded=False,
            error_text=reason,
        )
        self.append_run_event(
            run["id"],
            "run_finished",
            self._run_finished_event_payload(updated, status="failed", reason="orphaned_worker"),
        )
        return updated or run

    def _should_recover_local_orphan(self, run: dict) -> bool:
        if run.get("status") not in {"queued", "running"}:
            return False
        if self._is_run_active_locally(run["id"]):
            return False
        if run.get("runner_pid") not in {None, os.getpid()}:
            return False
        updated_at = self._parse_run_timestamp(run.get("updated_at") or run.get("started_at") or run.get("queued_at"))
        if updated_at is None:
            return False
        age_seconds = time.time() - updated_at.timestamp()
        return age_seconds >= self._local_run_orphan_grace_seconds()

    def _local_run_orphan_grace_seconds(self) -> float:
        return max(
            self.settings.stop_grace_period_seconds,
            self.settings.polling_interval_seconds * 4,
            self.settings.role_idle_timeout_seconds,
            30.0,
        )

    def _mark_run_active(self, run_id: str) -> None:
        cls = type(self)
        with cls._process_active_runs_lock:
            cls._process_active_runs.add(run_id)

    def _try_mark_run_active(self, run_id: str) -> bool:
        cls = type(self)
        with cls._process_active_runs_lock:
            if run_id in cls._process_active_runs:
                return False
            cls._process_active_runs.add(run_id)
            return True

    def _mark_run_inactive(self, run_id: str) -> None:
        cls = type(self)
        with cls._process_active_runs_lock:
            cls._process_active_runs.discard(run_id)

    def _is_run_active_locally(self, run_id: str) -> bool:
        cls = type(self)
        with cls._process_active_runs_lock:
            return run_id in cls._process_active_runs

    @staticmethod
    def _parse_run_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _pid_exists(pid: int | None) -> bool:
        if not pid:
            return False
        try:
            os.kill(int(pid), 0)
        except (ProcessLookupError, OSError):
            return False
        except PermissionError:
            return True
        return True
