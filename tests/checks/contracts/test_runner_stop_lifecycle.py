from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from loopora.executor import CodexExecutor, ExecutorError
from loopora.service import LooporaError

from runner_helpers import (
    _create_loop,
    _join_async_run,
    _wait_for_terminal_run,
)


MIN_ITERATIONS_BEFORE_STOP = 2


def _wait_until_generator_running(service, run_id: str) -> bool:
    deadline = time.time() + 5
    while time.time() < deadline:
        current = service.get_run(run_id)
        events = service.repository.list_events(run_id, after_id=0, limit=50)
        saw_generator_start = any(
            event["event_type"] == "role_started" and event.get("role") == "generator" for event in events
        )
        if current["status"] == "running" and saw_generator_start:
            return True
        time.sleep(0.05)
    return False


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
            deadline = time.time() + 0.4
            while time.time() < deadline:
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

    deadline = time.time() + 5
    while time.time() < deadline:
        current = service.get_run(run["id"])
        if current["current_iter"] >= MIN_ITERATIONS_BEFORE_STOP:
            break
        time.sleep(0.05)

    current = service.get_run(run["id"])
    assert current["status"] in {"queued", "running"}
    assert current["current_iter"] >= MIN_ITERATIONS_BEFORE_STOP

    service.stop_run(run["id"])

    stopped = _wait_for_terminal_run(service, run["id"])
    _join_async_run(service, run["id"])
    assert stopped["status"] == "stopped"


def test_stop_run_rejects_finished_runs(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Finished Loop")
    run = service.rerun(loop["id"])

    with pytest.raises(LooporaError, match="cannot stop run in status"):
        service.stop_run(run["id"])

    events = service.repository.list_events(run["id"], after_id=0, limit=1000)
    assert all(event["event_type"] != "stop_requested" for event in events)
