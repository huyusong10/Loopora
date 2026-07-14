from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from loopora.executor import CodexExecutor, ExecutorError
from loopora.events.streams import run_stream_id
from loopora.service import LooporaError
from loopora.service_types import ACTIVE_RUN_STATUSES

from runner_helpers import (
    _create_loop,
    _join_async_run,
    _wait_for_terminal_run,
)


MIN_STARTED_ITERATIONS_BEFORE_STOP = 2
ZERO_MAX_ITERS_PROGRESS_TIMEOUT_SECONDS = 15.0


def _wait_until_generator_running(service, run_id: str) -> bool:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = service.get_run(run_id)
        events = service.repository.list_events(run_id, after_id=0, limit=50)
        saw_generator_start = any(
            event["event_type"] == "role_started" and event.get("role") == "generator" for event in events
        )
        if current["status"] == "running" and saw_generator_start:
            return True
        time.sleep(0.05)
    return False


def _iteration_started_events(service, run_id: str):
    return [
        event
        for event in service.repository.list_domain_events(run_stream_id(run_id), limit=500)
        if event.event_type == "IterationStarted"
    ]


def _wait_for_started_iteration_count(service, run_id: str, min_count: int, *, timeout: float) -> tuple[dict, list]:
    deadline = time.monotonic() + timeout
    current = service.get_run(run_id)
    started_events = _iteration_started_events(service, run_id)
    while time.monotonic() < deadline:
        started_events = _iteration_started_events(service, run_id)
        current = service.get_run(run_id)
        if len(started_events) >= min_count or current["status"] not in ACTIVE_RUN_STATUSES:
            return current, started_events
        time.sleep(0.05)
    return current, started_events


def _progress_diagnostic(service, run_id: str, current: dict, started_events: list) -> dict:
    domain_events = service.repository.list_domain_events(run_stream_id(run_id), limit=500)
    run_events = service.repository.list_events(run_id, after_id=0, limit=500)
    thread = service._threads.get(run_id)
    return {
        "status": current.get("status"),
        "current_iter": current.get("current_iter"),
        "started_iterations": [event.payload.get("iteration") for event in started_events],
        "domain_tail": [
            {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "iteration": event.payload.get("iteration"),
                "step_id": event.payload.get("step_id"),
            }
            for event in domain_events[-10:]
        ],
        "run_event_tail": [
            {
                "id": event.get("id"),
                "event_type": event.get("event_type"),
                "role": event.get("role"),
                "iter": (event.get("payload") or {}).get("iter"),
                "step_id": (event.get("payload") or {}).get("step_id"),
            }
            for event in run_events[-10:]
        ],
        "thread_alive": bool(thread and thread.is_alive()),
    }


def _stop_active_async_run(service, run_id: str) -> dict:
    current = service.get_run(run_id)
    if current["status"] in ACTIVE_RUN_STATUSES:
        service.stop_run(run_id)
        current = _wait_for_terminal_run(service, run_id, timeout=10)
    _join_async_run(service, run_id, timeout=10)
    return current


def test_stop_run_marks_run_stopped(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success", role_delay=0.5)
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.start_run(loop["id"])

    thread = threading.Thread(target=service.execute_run, args=(run["id"],), daemon=True)
    thread.start()

    _wait_until_generator_running(service, run["id"])

    service.stop_run(run["id"])
    thread.join(timeout=5)

    stopped = service.get_run(run["id"])
    assert stopped["status"] == "stopped"


def test_stop_requested_run_does_not_retry_the_active_role(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class StopAwareExecutor(CodexExecutor):
        def execute(self, _request, _emit_event, should_stop, _set_child_pid):
            deadline = time.monotonic() + 0.4
            while time.monotonic() < deadline:
                if should_stop():
                    raise ExecutorError("terminated after stop request")
                time.sleep(0.01)
            return {
                "attempted": "noop",
                "abandoned": "",
                "assumption": "",
                "summary": "",
                "changed_files": [],
            }

    service = service_factory(scenario="success")
    service.executor_factory = StopAwareExecutor
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Stop Retry Guard")
    run = service.start_run(loop["id"])

    thread = threading.Thread(target=service.execute_run, args=(run["id"],), daemon=True)
    thread.start()

    saw_generator_start = _wait_until_generator_running(service, run["id"])

    service.stop_run(run["id"])
    thread.join(timeout=5)

    stopped = service.get_run(run["id"])
    assert stopped["status"] == "stopped"

    events = service.repository.list_events(run["id"], after_id=0, limit=200)
    generator_starts = [event for event in events if event["event_type"] == "role_started" and event.get("role") == "generator"]
    assert saw_generator_start is True
    assert len(generator_starts) == 1


def test_stop_queued_run_without_worker_finishes_immediately(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Queued Stop Loop")
    run = service.start_run(loop["id"])

    stopped = service.stop_run(run["id"])

    assert stopped["status"] == "stopped"
    assert service.get_run(run["id"])["status"] == "stopped"
    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert [event["event_type"] for event in events if event["event_type"] in {"stop_requested", "run_finished"}] == [
        "stop_requested",
        "run_finished",
    ]
    assert events[-1]["payload"]["reason"] == "stopped_before_start"

    next_run = service.start_run(loop["id"])
    assert next_run["id"] != run["id"]
    assert next_run["status"] == "queued"


def test_zero_max_iters_runs_until_stopped(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="plateau", role_delay=0.02)
    loop = service.create_loop(
        name="Infinite Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=0,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    service.start_run_async(run["id"])

    try:
        current, started_events = _wait_for_started_iteration_count(
            service,
            run["id"],
            MIN_STARTED_ITERATIONS_BEFORE_STOP,
            timeout=ZERO_MAX_ITERS_PROGRESS_TIMEOUT_SECONDS,
        )
        diagnostic = _progress_diagnostic(service, run["id"], current, started_events)
        assert current["status"] in {"queued", "running"}, diagnostic
        assert len(started_events) >= MIN_STARTED_ITERATIONS_BEFORE_STOP, diagnostic
        assert current["current_iter"] >= MIN_STARTED_ITERATIONS_BEFORE_STOP - 1, diagnostic
    finally:
        stopped = _stop_active_async_run(service, run["id"])

    assert stopped["status"] == "stopped"


def test_stop_run_rejects_finished_runs(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Finished Loop")
    run = service.rerun(loop["id"])

    with pytest.raises(LooporaError, match="cannot stop run in status"):
        service.stop_run(run["id"])

    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert all(event["event_type"] != "stop_requested" for event in events)
