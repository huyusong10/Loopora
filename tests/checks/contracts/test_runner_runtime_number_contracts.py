from __future__ import annotations

import math
from pathlib import Path

import pytest

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary
from loopora.context_step_results import StepEvidenceEntryRequest, StepResultContext, build_step_evidence_entry, build_step_handoff
from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaError

from runner_helpers import _create_loop


def test_run_contract_snapshot_rejects_bool_numeric_limits(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_contract_bool_limits")
    layout.initialize()

    snapshot = build_run_contract_snapshot(
        RunContractSnapshotRequest(
            run={
                "id": "run_bool_limits",
                "runs_dir": str(tmp_path),
                "compiled_spec_json": {},
                "completion_mode": "gatekeeper",
                "max_iters": True,
                "max_role_retries": True,
                "delta_threshold": 0.0,
                "trigger_window": True,
                "regression_window": True,
                "iteration_interval_seconds": 0.0,
            },
            compiled_spec={},
            strategy_source={"roles": [], "steps": []},
            prompt_files={},
            workspace_baseline={"file_count": True},
            layout=layout,
        )
    )

    assert (
        snapshot["max_iters"],
        snapshot["max_role_retries"],
        snapshot["trigger_window"],
        snapshot["regression_window"],
        snapshot["workspace_baseline"]["file_count"],
    ) == (0, 0, 0, 0, 0)


def test_step_artifact_contexts_reject_bool_identity(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "step_artifact_bool_identity")
    step = {"id": "builder_step"}
    role = {"id": "builder", "name": "Builder", "archetype": "builder"}
    result = StepResultContext(
        layout=layout,
        iter_id=True,
        step=step,
        step_order=True,
        role=role,
        runtime_role="builder",
        output={"summary": "Built the slice.", "changed_files": [], "proof_files": []},
    )

    handoff = build_step_handoff(result)
    evidence = build_step_evidence_entry(StepEvidenceEntryRequest(result=result, handoff=handoff))
    summary = build_iteration_summary(
        IterationSummaryContext(
            layout=layout,
            iter_id=True,
            step_results=[
                {"step": step, "step_order": True, "role": role, "runtime_role": "builder", "handoff": handoff, "output": {}}
            ],
            stagnation={},
            previous_composite=None,
            timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert handoff["source"]["iter"] == 0
    assert handoff["source"]["step_order"] == 0
    assert handoff["artifact_refs"][0]["relative_path"] == "iterations/iter_000/steps/00__builder_step/output.raw.json"
    assert (evidence["id"], evidence["iter"], evidence["step_order"]) == ("ev_000_00_builder_step", 0, 0)
    assert summary["iter"] == 0
    assert summary["latest_refs"]["latest_by_step"]["builder_step"] == "iterations/iter_000/steps/00__builder_step/handoff.json"


@pytest.mark.parametrize(
    "case",
    [
        ("iteration_interval_seconds", math.nan, "iteration_interval_seconds must be a finite number"),
        ("delta_threshold", math.inf, "delta_threshold must be a finite number"),
        ("max_iters", math.inf, "max_iters must be a finite number"),
        ("max_iters", False, "max_iters must be a finite number"),
        ("max_iters", 1.5, "max_iters must be an integer"),
        ("trigger_window", 1.5, "trigger_window must be an integer"),
        ("delta_threshold", -0.1, "delta_threshold must be >= 0"),
    ],
)
def test_create_loop_rejects_invalid_runtime_numbers(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    case: tuple[str, object, str],
) -> None:
    service = service_factory(scenario="success")
    field_name, value, error_text = case

    with pytest.raises(LooporaError, match=error_text):
        _create_loop(service, sample_spec_file, sample_workdir, **{field_name: value})
