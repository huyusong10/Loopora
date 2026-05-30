import logging

import pytest

from loopora.service_alignment_session_lifecycle import (
    AlignmentSessionLifecycleContext,
    alignment_thread_key,
    cancel_alignment_session,
    start_alignment_session_async,
)
from loopora.service_types import LooporaConflictError


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
    def __init__(self) -> None:
        self.started = False
        self.alive = False

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
    repo = FakeAlignmentLifecycleRepository({"id": "align_1", "status": "idle", "active_child_pid": 123})
    context, threads, thread, _diagnostic_events = lifecycle_context(repo)

    start_alignment_session_async(context, "align_1", active_statuses={"running", "validating"})

    assert repo.session["status"] == "running"
    assert repo.session["stop_requested"] is False
    assert repo.session["active_child_pid"] is None
    assert repo.updates[-1]["finished_at"] is None
    assert repo.events == [{"event_type": "alignment_started", "payload": {"status": "running"}}]
    assert threads["alignment:align_1"] is thread
    assert thread.started is True


def test_alignment_thread_key_is_stable_worker_identity() -> None:
    assert alignment_thread_key("align_1") == "alignment:align_1"


def test_start_alignment_session_lifecycle_rejects_active_session_or_live_thread() -> None:
    active_repo = FakeAlignmentLifecycleRepository({"id": "align_active", "status": "running"})
    active_context, _threads, _thread, _diagnostics = lifecycle_context(active_repo)

    with pytest.raises(LooporaConflictError, match="already running"):
        start_alignment_session_async(active_context, "align_active", active_statuses={"running"})

    idle_repo = FakeAlignmentLifecycleRepository({"id": "align_idle", "status": "idle"})
    idle_context, threads, thread, _diagnostics = lifecycle_context(idle_repo)
    thread.alive = True
    threads["alignment:align_idle"] = thread

    with pytest.raises(LooporaConflictError, match="already running"):
        start_alignment_session_async(idle_context, "align_idle", active_statuses={"running"})


def test_cancel_alignment_session_lifecycle_requests_stop_and_records_signal_diagnostic() -> None:
    repo = FakeAlignmentLifecycleRepository(
        {
            "id": "align_cancel",
            "status": "running",
            "active_child_pid": 987654,
        }
    )

    def fail_signal(_pid: int, _signal: int) -> None:
        raise OSError("signal denied")

    context, _threads, _thread, diagnostic_events = lifecycle_context(repo, signal_process=fail_signal)

    cancelled = cancel_alignment_session(
        context,
        "align_cancel",
        active_statuses={"running", "validating"},
        logger=logging.getLogger("tests.alignment.lifecycle"),
    )

    assert cancelled["stop_requested"] is True
    assert repo.events[0] == {"event_type": "alignment_cancel_requested", "payload": {"status": "running"}}
    assert diagnostic_events[0]["event_type"] == "alignment_cancel_signal_failed"
    assert diagnostic_events[0]["payload"]["operation"] == "alignment_cancel_signal"
    assert diagnostic_events[0]["payload"]["resource_type"] == "process"
    assert diagnostic_events[0]["payload"]["resource_id"] == "987654"
    assert diagnostic_events[0]["payload"]["owner_id"] == "align_cancel"


def test_cancel_alignment_session_lifecycle_rejects_inactive_session() -> None:
    repo = FakeAlignmentLifecycleRepository({"id": "align_idle", "status": "idle"})
    context, _threads, _thread, _diagnostics = lifecycle_context(repo)

    with pytest.raises(LooporaConflictError, match="cannot cancel"):
        cancel_alignment_session(
            context,
            "align_idle",
            active_statuses={"running"},
            logger=logging.getLogger("tests.alignment.lifecycle"),
        )
