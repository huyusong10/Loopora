from __future__ import annotations

from pathlib import Path

from loopora.kernel import VerdictStatus

from verdict_engine_parity_test_support import (
    LEGACY_TO_KERNEL_STATUS,
    base_compiled_spec,
    coverage_payload,
    legacy_and_kernel_statuses,
    refund_targets,
)


def test_verdict_engine_matches_legacy_for_managed_residual_risk(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec()
    coverage = coverage_payload(
        refund_targets(),
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "Manual billing export remains a visible follow-up.",
        },
    )

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.PASSED_WITH_RESIDUAL_RISK


def test_verdict_engine_matches_legacy_for_unmanaged_residual_risk(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec()
    coverage = coverage_payload(
        refund_targets(),
        latest_gatekeeper={"id": "ev_gatekeeper", "result": "passed", "residual_risk": "Some risk remains."},
    )

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_matches_legacy_for_disallowed_residual_risk(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec(residual_risk="Do not accept residual risk.")
    coverage = coverage_payload(
        refund_targets(),
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "Manual billing export remains a visible follow-up.",
        },
    )

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_ignores_superseded_historical_risk_after_clean_gatekeeper_pass(tmp_path: Path) -> None:
    compiled_spec = base_compiled_spec()
    coverage = coverage_payload(
        refund_targets(),
        risk_signals=["Earlier blocker was resolved by the latest Builder pass."],
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "No blocking residual risk was reported by GateKeeper.",
        },
    )

    legacy_status, kernel_status = legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.PASSED
