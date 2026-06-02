from __future__ import annotations

import os
from pathlib import Path

from loopora.service import LooporaService

from runner_helpers import _create_loop


def test_second_service_instance_does_not_recover_run_active_in_same_process(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Shared Process Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="running",
        runner_pid=os.getpid(),
        active_role="generator",
        started_at="2026-04-13T08:00:00+00:00",
    )
    service._mark_run_active(run["id"])

    try:
        restarted = LooporaService(
            repository=service.repository,
            settings=service.settings,
            executor_factory=service.executor_factory,
        )
        restarted._local_run_orphan_grace_seconds = lambda: 0.0  # type: ignore[method-assign]

        current = restarted.get_run(run["id"])

        assert current["status"] == "running"
        assert current["error_message"] in {None, ""}
    finally:
        service._mark_run_inactive(run["id"])


def test_second_service_instance_does_not_recover_queued_run_with_same_process_pid(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Queued Shared Process Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="queued",
        runner_pid=os.getpid(),
        started_at="2026-04-13T08:00:00+00:00",
    )
    service._mark_run_active(run["id"])

    try:
        restarted = LooporaService(
            repository=service.repository,
            settings=service.settings,
            executor_factory=service.executor_factory,
        )
        restarted._local_run_orphan_grace_seconds = lambda: 0.0  # type: ignore[method-assign]

        current = restarted.get_run(run["id"])

        assert current["status"] == "queued"
        assert current["error_message"] in {None, ""}
    finally:
        service._mark_run_inactive(run["id"])


def test_second_service_instance_keeps_fresh_queued_run_without_runner_pid(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Fresh Queued Loop")
    run = service.start_run(loop["id"])

    restarted = LooporaService(
        repository=service.repository,
        settings=service.settings,
        executor_factory=service.executor_factory,
    )

    current = restarted.get_run(run["id"])

    assert current["status"] == "queued"
    assert current["error_message"] in {None, ""}
