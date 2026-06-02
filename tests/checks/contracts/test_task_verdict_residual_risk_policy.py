from __future__ import annotations

from pathlib import Path
from typing import Any

from task_verdict_test_support import (
    build_passed_task_verdict,
    gatekeeper_residual_risk,
    write_task_verdict_covered_gatekeeper_coverage as _write_covered_coverage,
)


def test_task_verdict_does_not_pass_with_unmanaged_residual_risk(tmp_path: Path) -> None:
    risk = "Some residual risk remains."
    run_dir = tmp_path / "run_unmanaged_residual_risk"
    _write_covered_coverage(run_dir, latest_gatekeeper=gatekeeper_residual_risk(risk))

    task_verdict = build_passed_task_verdict(run_dir, residual_risks=[risk])

    _assert_unmanaged_residual_risk(task_verdict, risk)


def test_task_verdict_treats_vague_chinese_residual_risk_acceptance_as_unmanaged(tmp_path: Path) -> None:
    risk = "有些风险可以接受。"
    run_dir = tmp_path / "run_vague_chinese_residual_risk"
    _write_covered_coverage(run_dir, latest_gatekeeper=gatekeeper_residual_risk(risk))

    task_verdict = build_passed_task_verdict(run_dir, residual_risks=[risk])

    _assert_unmanaged_residual_risk(task_verdict, risk)


def test_task_verdict_does_not_treat_manual_or_visible_words_as_residual_risk_management(
    tmp_path: Path,
) -> None:
    risk = "Ownerless manual billing export remains visible."
    run_dir = tmp_path / "run_manual_visible_residual_risk"
    _write_covered_coverage(run_dir)

    task_verdict = build_passed_task_verdict(run_dir, residual_risks=[risk])

    _assert_unmanaged_residual_risk(task_verdict, risk)


def test_task_verdict_does_not_accept_residual_risk_when_run_contract_disallows_it(tmp_path: Path) -> None:
    risk = "Manual billing export remains visible as a follow-up owned by Support."
    run_dir = tmp_path / "run_disallowed_residual_risk"
    _write_covered_coverage(run_dir, latest_gatekeeper=gatekeeper_residual_risk(risk))

    task_verdict = build_passed_task_verdict(
        run_dir,
        residual_risks=[risk],
        compiled_residual_risk="No residual risk is acceptable; any remaining risk must fail closed.",
    )

    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == (
        "GateKeeper reported residual risk even though the run contract disallows accepted residual risk."
    )
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": risk,
            "reason": "Residual risk was reported even though the run contract disallows accepted residual risk.",
            "residual_risk_policy": "disallowed",
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def test_task_verdict_does_not_erase_negated_residual_risk_with_exception(tmp_path: Path) -> None:
    risk = "No blocking residual risk except untested billing export."
    run_dir = tmp_path / "run_excepted_residual_risk"
    _write_covered_coverage(run_dir, latest_gatekeeper=gatekeeper_residual_risk(risk))

    task_verdict = build_passed_task_verdict(run_dir, residual_risks=[risk])

    _assert_unmanaged_residual_risk(task_verdict, risk)


def test_task_verdict_classifies_unmanaged_coverage_risk_signal_as_weak(tmp_path: Path) -> None:
    risk = "Some residual risk remains."
    run_dir = tmp_path / "run_unmanaged_coverage_risk"
    _write_covered_coverage(run_dir, risk_signals=[risk])

    task_verdict = build_passed_task_verdict(run_dir)

    assert task_verdict["status"] == "passed"
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": risk,
            "reason": "Residual risk was observed without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []


def _assert_unmanaged_residual_risk(task_verdict: dict[str, Any], label: str) -> None:
    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["summary"] == "GateKeeper reported residual risk without a named owner, follow-up, or acceptance path."
    assert task_verdict["buckets"]["weak"] == [
        {
            "label": label,
            "reason": "Residual risk was reported without enough management detail to accept it.",
            "managed": False,
        }
    ]
    assert task_verdict["buckets"]["residual_risk"] == []
