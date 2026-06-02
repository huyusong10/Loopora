from __future__ import annotations

from pathlib import Path

import pytest

from task_verdict_test_support import (
    build_passed_task_verdict,
    gatekeeper_residual_risk,
    write_task_verdict_covered_gatekeeper_coverage as _write_covered_coverage,
)


def test_task_verdict_omits_historical_risks_after_clean_gatekeeper_pass(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_superseded_residual_risk"
    _write_covered_coverage(
        run_dir,
        summary_reason="Required and advisory coverage targets have supporting evidence.",
        risk_signals=[
            "Admin presentation remains for downstream inspection rather than this Builder pass.",
            "Blocking: rollback/replay/audit preservation remains unproven and must be owned by the next Builder pass.",
        ],
        latest_gatekeeper=gatekeeper_residual_risk("No blocking residual risk was reported by GateKeeper."),
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper accepted the current evidence.",
    )

    assert task_verdict["status"] == "passed"
    assert task_verdict["buckets"]["weak"] == []
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_hides_superseded_historical_residual_risk_after_gatekeeper_pass(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_historical_residual_risk"
    _write_covered_coverage(
        run_dir,
        summary_reason="GateKeeper passed after earlier risk was resolved.",
        risk_signals=["Earlier blocked iteration named a risk that is no longer part of the final pass."],
        latest_gatekeeper=gatekeeper_residual_risk("No blocking residual risk was reported by GateKeeper."),
    )

    task_verdict = build_passed_task_verdict(
        run_dir,
        decision_summary="GateKeeper passed without accepted residual risk.",
    )

    assert task_verdict["status"] == "passed"
    assert task_verdict["source"] == "gatekeeper"
    assert task_verdict["buckets"]["weak"] == []
    assert task_verdict["buckets"]["residual_risk"] == []


@pytest.mark.parametrize(
    ("run_name", "risk_marker", "decision_summary"),
    [
        (
            "run_no_residual_risk_marker",
            "无残余风险",
            "GateKeeper passed without accepted residual risk.",
        ),
        (
            "run_no_meaningful_chinese_residual_risk_marker",
            "无重大残余风险",
            "GateKeeper passed without meaningful residual risk.",
        ),
    ],
)
def test_task_verdict_keeps_pass_when_gatekeeper_reports_no_residual_risk_markers(
    tmp_path: Path,
    run_name: str,
    risk_marker: str,
    decision_summary: str,
) -> None:
    run_dir = tmp_path / run_name
    _write_covered_coverage(
        run_dir,
        summary_reason="GateKeeper passed with no accepted residual risk.",
        latest_gatekeeper=gatekeeper_residual_risk(risk_marker),
    )

    task_verdict = build_passed_task_verdict(run_dir, decision_summary=decision_summary)

    assert task_verdict["status"] == "passed"
    assert task_verdict["buckets"]["residual_risk"] == []
