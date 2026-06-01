from __future__ import annotations

import math
from pathlib import Path

import pytest

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.context_iteration_summary import (
    IterationSummaryContext,
    build_iteration_summary,
)
from loopora.context_step_results import (
    StepEvidenceEntryRequest,
    StepResultContext,
    build_step_evidence_entry,
    build_step_handoff,
)
from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaError
from loopora.service_iteration_reporting import IterationReportContext, IterationSummaryRequest
from loopora.service_types import LooporaNotFoundError
import loopora.service_cleanup_diagnostics as cleanup_diagnostics

from runner_helpers import (
    _create_loop,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


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
            step_results=[{"step": step, "step_order": True, "role": role, "runtime_role": "builder", "handoff": handoff, "output": {}}],
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


def test_iteration_reporting_requires_literal_passed_booleans(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    compiled_spec = {
        "checks": [{"id": "check_1", "title": "Main check"}],
        "check_mode": "specified",
    }
    tester_result = service._enrich_tester_result(
        {
            "execution_summary": {"total_checks": 1, "passed": 1, "failed": 0, "errored": 0, "total_duration_ms": 1},
            "check_results": [{"id": "check_1", "title": "Main check", "status": "passed", "notes": "ok"}],
            "dynamic_checks": [],
            "tester_observations": "",
        }
    )
    verifier_result = service._enrich_verifier_result(
        {
            "passed": "true",
            "decision_summary": "Raw string pass should not be trusted.",
            "composite_score": "1.0",
            "metric_scores": {
                "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                "quality_score": {"value": 1.0, "threshold": 0.9, "passed": "true"},
            },
            "failed_check_ids": [],
            "hard_constraint_violations": [],
            "priority_failures": [],
            "feedback_to_generator": "",
            "evidence_refs": [],
        },
        compiled_spec,
        tester_result,
    )

    assert verifier_result["passed"] is False
    assert verifier_result["composite_score"] == 0.0
    assert verifier_result["failing_metrics"] == [{"name": "quality_score", "value": 1.0, "threshold": 0.9}]
    assert "Task verdict is not ready" in verifier_result["decision_summary"]

    report = IterationReportContext(
        iter_id=0,
        generator_result={"attempted": "", "summary": "", "assumption": "", "abandoned": "", "changed_files": []},
        tester_result=tester_result,
        verifier_result=verifier_result,
        stagnation={
            "stagnation_mode": "none",
            "recent_composites": ["0.9", 0.8, True],
            "recent_deltas": ["0.1", 0.2, False],
            "consecutive_low_delta": "2",
        },
        generator_mode="default",
        tester_mode="default",
        verifier_mode="default",
        previous_composite=None,
    )
    log_entry = service._build_iteration_log_entry(report)
    summary = service._build_summary(
        IterationSummaryRequest(
            run={
                "workdir": str(sample_workdir),
                "completion_mode": "gatekeeper",
                "iteration_interval_seconds": 0.0,
            },
            compiled_spec=compiled_spec,
            report=report,
        )
    )

    assert log_entry["score"]["passed"] is False
    assert log_entry["verifier"]["passed"] is False
    assert log_entry["stagnation"]["recent_composites"] == [0.8]
    assert log_entry["stagnation"]["recent_deltas"] == [0.2]
    assert log_entry["stagnation"]["consecutive_low_delta"] == 0
    assert "- Passed: `False`" in summary
    assert "Still iterating." in summary
    assert "All checks passed in this iteration." not in summary


def test_gatekeeper_composite_score_requires_literal_number(service_factory) -> None:
    service = service_factory(scenario="success")

    gatekeeper_result = service._coerce_gatekeeper_output(
        {
            "passed": False,
            "decision_summary": "Blocked with a malformed score.",
            "composite_score": "0.95",
            "blocking_issues": ["missing proof"],
            "evidence_refs": [],
        }
    )

    assert gatekeeper_result["passed"] is False
    assert gatekeeper_result["composite_score"] == 0.0


def test_asset_call_does_not_classify_plain_unknown_validation_errors_as_not_found(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="unknown is just part of this validation message") as exc_info:
        service._asset_call(lambda: (_ for _ in ()).throw(ValueError("unknown is just part of this validation message")))

    assert not isinstance(exc_info.value, LooporaNotFoundError)


def test_loop_delete_logs_artifact_cleanup_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    log_calls: list[dict] = []

    def fail_rmtree(path: Path) -> None:
        if Path(path) == Path(run["runs_dir"]):
            raise OSError("run dir locked")
        return

    def capture_log_event(_logger, _level, event, message, **context):
        log_calls.append({"event": event, "message": message, "context": context})

    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", capture_log_event)
    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert any(
        call["event"] == "service.cleanup.failed"
        and call["context"].get("operation") == "loop_artifact_delete"
        and call["context"].get("owner_id") == loop["id"]
        for call in log_calls
    )


def test_loop_delete_logs_registry_mark_failure_without_failing(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir)
    run = service.rerun(loop["id"])
    log_calls: list[dict] = []

    def fail_registry_mark(*, path: Path, state: str) -> int:
        assert state in {"cleaned", "orphaned"}
        if Path(path) == Path(run["runs_dir"]):
            raise RuntimeError("registry write failed")
        return 1

    def capture_log_event(_logger, _level, event, message, **context):
        log_calls.append({"event": event, "message": message, "context": context})

    monkeypatch.setattr(service.repository, "mark_local_asset_root_state_by_path", fail_registry_mark)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", capture_log_event)
    result = service.delete_loop(loop["id"])

    assert result["id"] == loop["id"]
    assert any(
        call["event"] == "service.cleanup.failed"
        and call["context"].get("operation") == "loop_artifact_delete_registry_mark"
        and call["context"].get("owner_id") == loop["id"]
        for call in log_calls
    )


def test_loop_deletion_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    deletion_source = (REPO_ROOT / "src" / "loopora" / "service_loop_deletion.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_loop_deletion import ServiceLoopDeletionMixin" in lifecycle_source
    assert "def delete_loop" not in lifecycle_source
    assert "def delete_loop" in deletion_source
    assert "def _mark_local_asset_cleanup_by_path" in deletion_source
    assert "service_loop_deletion.py" in design_source


@pytest.mark.parametrize(
    "case",
    (
        ("iteration_interval_seconds", math.nan, "iteration_interval_seconds must be a finite number"),
        ("delta_threshold", math.inf, "delta_threshold must be a finite number"),
        ("max_iters", math.inf, "max_iters must be a finite number"),
        ("max_iters", False, "max_iters must be a finite number"),
        ("max_iters", 1.5, "max_iters must be an integer"),
        ("trigger_window", 1.5, "trigger_window must be an integer"),
        ("delta_threshold", -0.1, "delta_threshold must be >= 0"),
    ),
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
