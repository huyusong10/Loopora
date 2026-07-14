from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from loopora.service import LooporaError

from runner_helpers import (
    _create_loop,
    _join_async_run,
    _wait_for_terminal_run,
)


def test_same_workdir_concurrent_run_is_rejected(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    first_loop = _create_loop(service, sample_spec_file, sample_workdir, name="First")
    second_loop = _create_loop(service, sample_spec_file, sample_workdir, name="Second")

    first_run = service.start_run(first_loop["id"])
    service.start_run_async(first_run["id"])

    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = service.get_run(first_run["id"])["status"]
            if status == "running":
                break
            time.sleep(0.05)

        with pytest.raises(LooporaError):
            service.start_run(second_loop["id"])
    finally:
        if service.get_run(first_run["id"])["status"] in {"queued", "running"}:
            service.stop_run(first_run["id"])
            _wait_for_terminal_run(service, first_run["id"])
        _join_async_run(service, first_run["id"])


def test_start_run_async_rejects_duplicate_local_dispatch(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Duplicate Async Dispatch")
    run = service.start_run(loop["id"])
    service.start_run_async(run["id"])

    try:
        with pytest.raises(LooporaError, match="already executing in this process"):
            service.start_run_async(run["id"])
    finally:
        current = service.get_run(run["id"])
        if current["status"] in {"queued", "running"}:
            service.stop_run(run["id"])
            _wait_for_terminal_run(service, run["id"])
        _join_async_run(service, run["id"])


def test_execute_run_rejects_duplicate_local_worker(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Duplicate Worker")
    run = service.start_run(loop["id"])

    thread = threading.Thread(target=service.execute_run, args=(run["id"],), daemon=True)
    thread.start()

    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not service._is_run_active_locally(run["id"]):
            time.sleep(0.01)

        with pytest.raises(LooporaError, match="already executing in this process"):
            service.execute_run(run["id"])
    finally:
        current = service.get_run(run["id"])
        if current["status"] in {"queued", "running"}:
            service.stop_run(run["id"])
            _wait_for_terminal_run(service, run["id"])
        thread.join(timeout=5)


def test_async_run_cleans_up_thread_bookkeeping(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success", role_delay=0.01)
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Async Loop")
    run = service.start_run(loop["id"])
    service.start_run_async(run["id"])

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = service.get_run(run["id"])
        if current["status"] in {"succeeded", "failed", "stopped"}:
            break
        time.sleep(0.05)

    finished = service.get_run(run["id"])
    assert finished["status"] == "succeeded"
    assert run["id"] not in service._threads


def test_execute_run_returns_terminal_run_without_active_runtime_markers(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Runtime Marker Cleanup Loop")
    run = service.start_run(loop["id"])

    finished = service.execute_run(run["id"])

    assert finished["status"] == "succeeded"
    assert finished["active_role"] is None
    assert finished["runner_pid"] is None
    assert finished["child_pid"] is None
    stored = service.repository.get_run(run["id"])
    assert stored["active_role"] is None
    assert stored["runner_pid"] is None
    assert stored["child_pid"] is None
