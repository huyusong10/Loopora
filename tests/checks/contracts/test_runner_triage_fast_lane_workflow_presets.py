from __future__ import annotations

from pathlib import Path

from runner_helpers import _create_loop, complete_strategy_archetypes


def test_triage_first_workflow_runs_inspector_then_guide_then_builder(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Triage First Loop",
        workflow={"preset": "triage_first"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["workflow_json"]["preset"] == "triage_first"
    assert [step["role_id"] for step in run["workflow_json"]["steps"][:4]] == [
        "inspector",
        "guide",
        "builder",
        "gatekeeper",
    ]
    assert complete_strategy_archetypes(run)[:4] == [
        "inspector",
        "guide",
        "builder",
        "gatekeeper",
    ]


def test_fast_lane_workflow_runs_builder_before_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Fast Lane Loop",
        workflow={"preset": "fast_lane"},
    )

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert run["workflow_json"]["preset"] == "fast_lane"
    assert complete_strategy_archetypes(run)[:2] == ["builder", "gatekeeper"]
