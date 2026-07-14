import logging

import pytest

from loopora.service_alignment_session_lifecycle import (
    AlignmentSessionLifecycleContext,
    alignment_thread_key,
    cancel_alignment_session,
    start_alignment_session_async,
    start_alignment_session_sync,
)
from loopora.service_types import LooporaConflictError
from loopora.service_alignment_failure_recovery import ALIGNMENT_WORKER_START_ERROR


class FakeAlignmentLifecycleRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []
        self.updates: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.updates.append(fields)
        self.session.update(fields)
        if fields.get("clear_active_child_pid"):
            self.session["active_child_pid"] = None
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event

    def request_alignment_stop(self, session_id: str) -> dict:
        assert session_id == self.session["id"]
        self.session["stop_requested"] = True
        return dict(self.session)


class FakeAlignmentThread:
    started = False
    alive = False

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        return self.alive


def lifecycle_context(repo: FakeAlignmentLifecycleRepository, *, thread: FakeAlignmentThread | None = None, signal_process=None):
    threads: dict[str, FakeAlignmentThread] = {}
    diagnostic_events: list[dict] = []
    created_thread = thread or FakeAlignmentThread()

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def append_diagnostic_event(session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == repo.session["id"]
        event = {"event_type": event_type, "payload": payload}
        diagnostic_events.append(event)
        repo.events.append(event)
        return event

    context = AlignmentSessionLifecycleContext(
        repository=repo,
        get_session=get_session,
        execute_session=lambda _session_id: None,
        threads=threads,
        thread_key=alignment_thread_key,
        append_diagnostic_event=append_diagnostic_event,
        thread_factory=lambda _session_id, _execute_session: created_thread,
        signal_process=signal_process or (lambda _pid, _signal: None),
    )
    return context, threads, created_thread, diagnostic_events


def test_start_alignment_session_lifecycle_updates_state_event_and_thread() -> None:
    repo = lifecycle_repo("align_1", "idle", active_child_pid=123)
    context, threads, thread, _diagnostic_events = lifecycle_context(repo)

    start_alignment_session_async(context, "align_1", active_statuses={"running", "validating"})

    assert repo.session["status"] == "running"
    assert repo.session["stop_requested"] is False
    assert repo.session["active_child_pid"] is None
    assert repo.updates[-1]["finished_at"] is None
    assert repo.events == [{"event_type": "alignment_started", "payload": {"status": "running"}}]
    assert threads["alignment:align_1"] is thread
    assert thread.started is True


def test_start_alignment_session_sync_runs_without_background_thread() -> None:
    repo = lifecycle_repo("align_sync", "idle", active_child_pid=123)
    executed: list[str] = []
    context, threads, thread, _diagnostic_events = lifecycle_context(repo)
    context = AlignmentSessionLifecycleContext(
        repository=context.repository,
        get_session=context.get_session,
        execute_session=executed.append,
        threads=context.threads,
        thread_key=context.thread_key,
        append_diagnostic_event=context.append_diagnostic_event,
        thread_factory=context.thread_factory,
        signal_process=context.signal_process,
    )

    start_alignment_session_sync(context, "align_sync", active_statuses={"running", "validating"})

    assert executed == ["align_sync"]
    assert repo.session["status"] == "running"
    assert repo.session["stop_requested"] is False
    assert repo.session["active_child_pid"] is None
    assert repo.events == [{"event_type": "alignment_started", "payload": {"status": "running"}}]
    assert threads == {}
    assert thread.started is False


def test_alignment_thread_key_is_stable_worker_identity() -> None:
    assert alignment_thread_key("align_1") == "alignment:align_1"


def test_start_alignment_session_lifecycle_rejects_active_session_or_live_thread() -> None:
    active_repo = lifecycle_repo("align_active", "running")
    active_context, _threads, _thread, _diagnostics = lifecycle_context(active_repo)

    with pytest.raises(LooporaConflictError, match="already running"):
        start_alignment_session_async(active_context, "align_active", active_statuses={"running"})

    idle_repo = lifecycle_repo("align_idle", "idle")
    idle_context, threads, thread, _diagnostics = lifecycle_context(idle_repo)
    thread.alive = True
    threads["alignment:align_idle"] = thread

    with pytest.raises(LooporaConflictError, match="already running"):
        start_alignment_session_async(idle_context, "align_idle", active_statuses={"running"})


def test_start_alignment_session_lifecycle_persists_recoverable_thread_start_failure() -> None:
    repo = lifecycle_repo("align_start_failed", "idle")
    context, threads, thread, _diagnostics = lifecycle_context(repo)

    def fail_start() -> None:
        raise RuntimeError("private thread startup detail")

    thread.start = fail_start  # type: ignore[method-assign]
    start_alignment_session_async(context, "align_start_failed", active_statuses={"running"})

    assert threads == {}
    assert repo.session["status"] == "failed"
    assert repo.session["error_message"] == ALIGNMENT_WORKER_START_ERROR
    assert repo.events[-1] == {
        "event_type": "alignment_failed",
        "payload": {"status": "failed", "error": ALIGNMENT_WORKER_START_ERROR, "reason": "worker_start_failed"},
    }
    assert "private thread startup detail" not in str(repo.events)


def test_cancel_alignment_session_lifecycle_requests_stop_and_records_signal_diagnostic() -> None:
    repo = lifecycle_repo("align_cancel", "running", active_child_pid=987654)

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    context, _threads, _thread, diagnostic_events = lifecycle_context(repo, signal_process=fail_signal)

    cancelled = cancel_session(context, "align_cancel", active_statuses={"running", "validating"})

    assert cancelled["stop_requested"] is True
    assert repo.events[0] == {"event_type": "alignment_cancel_requested", "payload": {"status": "running"}}
    assert diagnostic_events[0]["event_type"] == "alignment_cancel_signal_failed"
    assert diagnostic_events[0]["payload"].items() >= {"operation": "alignment_cancel_signal", "resource_type": "process", "resource_id": "987654", "owner_id": "align_cancel"}.items()


def test_cancel_alignment_session_lifecycle_rejects_inactive_session() -> None:
    repo = lifecycle_repo("align_idle", "idle")
    context, _threads, _thread, _diagnostics = lifecycle_context(repo)

    with pytest.raises(LooporaConflictError, match="cannot cancel"):
        cancel_session(context, "align_idle")


def lifecycle_repo(session_id: str, status: str, **fields: object) -> FakeAlignmentLifecycleRepository:
    return FakeAlignmentLifecycleRepository({"id": session_id, "status": status, **fields})


def cancel_session(context: AlignmentSessionLifecycleContext, session_id: str, *, active_statuses: set[str] | None = None) -> dict:
    return cancel_alignment_session(context, session_id, active_statuses=active_statuses or {"running"}, logger=logging.getLogger("tests.alignment.lifecycle"))
