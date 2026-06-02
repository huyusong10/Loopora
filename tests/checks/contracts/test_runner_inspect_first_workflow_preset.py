from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop
from runner_workflow_preset_test_support import complete_strategy_archetypes


def test_inspect_first_workflow_runs_inspector_before_builder(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Inspect First Loop",
        workflow={"preset": "inspect_first"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["strategy_source"] == run["workflow_json"]
    assert run["workflow_json"]["preset"] == "inspect_first"
    assert complete_strategy_archetypes(run)[:3] == [
        "inspector",
        "builder",
        "gatekeeper",
    ]
