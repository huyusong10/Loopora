from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from datetime import datetime
import logging
import os
import signal
import time
from typing import Protocol

from loopora.diagnostics import get_logger, log_event, log_exception
from loopora.service_alignment_failure_recovery import ALIGNMENT_WORKER_INTERRUPTED_ERROR
from loopora.utils import utc_now
from loopora.workdir_inputs import same_workdir_identity

logger = get_logger(__name__)


class AlignmentRecoveryRepository(Protocol):
    def list_active_alignment_sessions(self, active_statuses: set[str]) -> list[dict]: ...

    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


class AlignmentRecoveryThread(Protocol):
    def is_alive(self) -> bool: ...


@dataclass(frozen=True)
class AlignmentRecoveryContext:
    repository: AlignmentRecoveryRepository
    threads: MutableMapping[str, AlignmentRecoveryThread]
    thread_key: Callable[[str], str]
    active_statuses: set[str]
    orphan_grace_seconds: float
    pid_exists: Callable[[int | None], bool]
    signal_process: Callable[[int, int], None] = os.kill
    now: Callable[[], str] = utc_now
    epoch: Callable[[], float] = time.time


def orphaned_alignment_sessions(
    context: AlignmentRecoveryContext,
    *,
    workdir: str = "",
) -> list[dict]:
    return [
        session
        for session in context.repository.list_active_alignment_sessions(context.active_statuses)
        if (not workdir or same_workdir_identity(session.get("workdir"), workdir))
        and _alignment_session_is_orphaned(context, session)
    ]


def reconcile_orphaned_alignment_sessions(
    context: AlignmentRecoveryContext,
    *,
    workdir: str = "",
) -> list[str]:
    recovered: list[str] = []
    for session in orphaned_alignment_sessions(context, workdir=workdir):
        _recover_orphaned_alignment_session(context, session)
        recovered.append(str(session["id"]))
    return recovered


def _alignment_session_is_orphaned(context: AlignmentRecoveryContext, session: dict) -> bool:
    if str(session.get("status") or "") not in context.active_statuses:
        return False
    session_id = str(session.get("id") or "")
    thread = context.threads.get(context.thread_key(session_id))
    if thread is not None:
        return not thread.is_alive()
    child_pid = _normalized_pid(session.get("active_child_pid"))
    if session.get("stop_requested"):
        return True
    if child_pid is not None:
        return not context.pid_exists(child_pid)
    updated_at = _parse_timestamp(session.get("updated_at") or session.get("created_at"))
    if updated_at is None:
        return False
    return context.epoch() - updated_at.timestamp() >= max(0.0, context.orphan_grace_seconds)


def _recover_orphaned_alignment_session(context: AlignmentRecoveryContext, session: dict) -> None:
    session_id = str(session["id"])
    user_cancelled = bool(session.get("stop_requested"))
    if user_cancelled:
        _stop_cancelled_orphan_child(context, session)
    error = "Cancelled by user." if user_cancelled else ALIGNMENT_WORKER_INTERRUPTED_ERROR
    event_type = "alignment_cancelled" if user_cancelled else "alignment_interrupted"
    reason = "orphaned_worker_after_cancel" if user_cancelled else "local_worker_interrupted"
    context.repository.update_alignment_session(
        session_id,
        status="failed",
        finished_at=context.now(),
        clear_active_child_pid=True,
        error_message=error,
    )
    context.repository.append_alignment_event(
        session_id,
        event_type,
        {"status": "failed", "error": error, "reason": reason},
    )
    context.threads.pop(context.thread_key(session_id), None)
    log_event(
        logger,
        logging.WARNING,
        "service.alignment.recovered_orphan",
        "Recovered orphaned planning session after its local worker stopped",
        session_id=session_id,
        workdir=session.get("workdir"),
        previous_status=session.get("status"),
        active_child_pid=session.get("active_child_pid"),
        recovery_reason=reason,
    )


def _stop_cancelled_orphan_child(context: AlignmentRecoveryContext, session: dict) -> None:
    child_pid = _normalized_pid(session.get("active_child_pid"))
    if child_pid is None or not context.pid_exists(child_pid):
        return
    try:
        context.signal_process(child_pid, signal.SIGTERM)
    except OSError as exc:
        log_exception(
            logger,
            "service.alignment.orphan_child_stop_failed",
            "Failed to stop orphaned planning child process after cancellation",
            error=exc,
            session_id=session.get("id"),
            workdir=session.get("workdir"),
            child_pid=child_pid,
        )


def alignment_process_exists(pid: int | None) -> bool:
    normalized = _normalized_pid(pid)
    if normalized is None:
        return False
    try:
        os.kill(normalized, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _normalized_pid(value: object) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _parse_timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
