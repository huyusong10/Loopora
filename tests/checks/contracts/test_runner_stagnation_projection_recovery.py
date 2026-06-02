from __future__ import annotations

import json
from pathlib import Path

from loopora.run_artifacts import RunArtifactLayout

from runner_helpers import _create_loop


def test_workflow_run_recovers_corrupt_stagnation_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Corrupt Stagnation Loop")
    queued = service.start_run(loop["id"])
    layout = RunArtifactLayout(Path(queued["runs_dir"]))
    layout.timeline_stagnation_path.write_text("{", encoding="utf-8")

    run = service.execute_run(queued["id"])
    stagnation = json.loads(layout.timeline_stagnation_path.read_text(encoding="utf-8"))

    assert run["status"] == "succeeded"
    assert "Expecting" not in str(run.get("error_message") or "")
    assert stagnation["stagnation_mode"] == "none"
