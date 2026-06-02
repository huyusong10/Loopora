from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop


def test_failed_run_without_verdict_is_not_evaluated(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Failed Without Verdict Loop")
    run = service.start_run(loop["id"])

    service.repository.update_run(run["id"], status="failed", error_message="setup failed before evidence")
    refreshed = service.get_run(run["id"])

    assert refreshed["run_status"] == "failed"
    assert refreshed["task_verdict"]["status"] == "not_evaluated"
    assert refreshed["task_verdict"]["source"] == "run_status"
