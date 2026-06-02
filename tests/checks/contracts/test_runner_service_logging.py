from __future__ import annotations

import json
from pathlib import Path

from loopora.settings import app_home, configure_logging

from runner_helpers import _create_loop


def test_successful_run_emits_structured_service_logs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    configure_logging()
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Diagnostic Loop")

    run = service.rerun(loop["id"])

    run_records = [
        json.loads(line)
        for line in (app_home() / "logs" / "service.log").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    run_records = [record for record in run_records if record.get("run_id") == run["id"]]
    events = {record["event"] for record in run_records}

    assert "service.run.execution.started" in events
    assert "service.runner.execution.started" in events
    assert "service.runner.iteration.started" in events
    assert "service.runner.step.completed" in events
    assert "service.run.execution.finished" in events
    finished_record = next(record for record in run_records if record["event"] == "service.run.execution.finished")
    assert finished_record["loop_id"] == loop["id"]
