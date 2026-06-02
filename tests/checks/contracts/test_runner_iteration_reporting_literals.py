from __future__ import annotations

from pathlib import Path

from loopora.service_iteration_reporting import IterationReportContext, IterationSummaryRequest


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
