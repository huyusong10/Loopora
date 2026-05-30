from __future__ import annotations

import os
import signal
import threading
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Protocol

from loopora.service_cleanup_diagnostics import cleanup_diagnostic_payload, log_cleanup_diagnostic
from loopora.service_types import LooporaConflictError


class AlignmentLifecycleRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...

    def request_alignment_stop(self, session_id: str) -> dict: ...


class AlignmentThread(Protocol):
    def start(self) -> None: ...

    def is_alive(self) -> bool: ...


def default_alignment_thread_factory(session_id: str, execute_session: Callable[[str], None]) -> AlignmentThread:
    return threading.Thread(
        target=execute_session,
        args=(session_id,),
        daemon=True,
        name=f"alignment-{session_id}",
    )


def alignment_thread_key(session_id: str) -> str:
    return f"alignment:{session_id}"


@dataclass(frozen=True)
class AlignmentSessionLifecycleContext:
    repository: AlignmentLifecycleRepository
    get_session: Callable[[str], dict]
    execute_session: Callable[[str], None]
    threads: MutableMapping[str, AlignmentThread]
    thread_key: Callable[[str], str]
    append_diagnostic_event: Callable[[str, str, dict], dict]
    thread_factory: Callable[[str, Callable[[str], None]], AlignmentThread] = default_alignment_thread_factory
    signal_process: Callable[[int, int], None] = os.kill


def start_alignment_session_async(context: AlignmentSessionLifecycleContext, session_id: str, *, active_statuses: set[str]) -> None:
    session = context.get_session(session_id)
    if session["status"] in active_statuses:
        raise LooporaConflictError("alignment session is already running")
    key = context.thread_key(session_id)
    thread = context.threads.get(key)
    if thread and thread.is_alive():
        raise LooporaConflictError("alignment session is already running")
    context.repository.update_alignment_session(
        session_id,
        status="running",
        stop_requested=False,
        clear_active_child_pid=True,
        finished_at=None,
        error_message="",
    )
    context.repository.append_alignment_event(session_id, "alignment_started", {"status": "running"})
    thread = context.thread_factory(session_id, context.execute_session)
    context.threads[key] = thread
    try:
        thread.start()
    except Exception:
        context.threads.pop(key, None)
        raise


def cancel_alignment_session(
    context: AlignmentSessionLifecycleContext,
    session_id: str,
    *,
    active_statuses: set[str],
    logger,
) -> dict:
    session = context.get_session(session_id)
    if session["status"] not in active_statuses:
        raise LooporaConflictError(f"cannot cancel alignment session in status {session['status']}")
    updated = context.repository.request_alignment_stop(session_id)
    context.repository.append_alignment_event(
        session_id,
        "alignment_cancel_requested",
        {"status": updated.get("status") if updated else session["status"]},
    )
    pid = session.get("active_child_pid")
    if pid not in {None, ""}:
        try:
            context.signal_process(int(pid), signal.SIGTERM)
        except (OSError, ValueError) as exc:
            diagnostic = cleanup_diagnostic_payload(
                operation="alignment_cancel_signal",
                resource_type="process",
                resource_id=pid,
                owner_id=session_id,
                error=exc,
                status=updated.get("status") if updated else session["status"],
            )
            log_cleanup_diagnostic(logger, **diagnostic)
            context.append_diagnostic_event(
                session_id,
                "alignment_cancel_signal_failed",
                diagnostic,
            )
    return context.get_session(session_id)
