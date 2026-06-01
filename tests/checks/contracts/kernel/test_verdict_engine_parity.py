from __future__ import annotations

import json
from pathlib import Path

from loopora.compiler import compile_loop_contract
from loopora.engine import verdict_from_legacy_coverage_projection
from loopora.kernel import VerdictStatus
from loopora.task_verdicts import build_task_verdict


LEGACY_TO_KERNEL_STATUS = {
    "passed": VerdictStatus.PASSED,
    "passed_with_residual_risk": VerdictStatus.PASSED_WITH_RESIDUAL_RISK,
    "insufficient_evidence": VerdictStatus.CONTINUE_REQUIRED,
    "failed": VerdictStatus.BLOCKED,
}


def _base_compiled_spec(*, residual_risk: object = None) -> dict:
    spec = {
        "goal": "Prove refund safety.",
        "checks": [{"id": "permission", "title": "Permission proof"}],
        "fake_done_states": ["Refund without audit trail."],
    }
    if residual_risk is not None:
        spec["residual_risk"] = residual_risk
    return spec


def _coverage_payload(
    targets: list[dict],
    *,
    risk_signals: list[str] | None = None,
    latest_gatekeeper: dict | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "status": "covered",
        "summary": {"reason": "Coverage projection fixture."},
        "targets": targets,
        "risk_signals": risk_signals or [],
        "latest_gatekeeper": latest_gatekeeper or {},
    }


def _target(target_id: str, label: str, status: str, *, required: bool) -> dict:
    return {
        "id": target_id,
        "label": label,
        "status": status,
        "required": required,
        "evidence_refs": ["ev_support"] if status == "covered" else [],
    }


def _legacy_and_kernel_statuses(
    tmp_path: Path,
    *,
    compiled_spec: dict,
    coverage: dict,
    raw_verdict: dict,
) -> tuple[str, VerdictStatus]:
    run_dir = tmp_path / "run"
    coverage_path = run_dir / "evidence" / "coverage.json"
    coverage_path.parent.mkdir(parents=True)
    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
    legacy = build_task_verdict(
        {
            "status": "succeeded",
            "compiled_spec": compiled_spec,
            "last_verdict_json": raw_verdict,
        },
        run_dir=run_dir,
    )
    kernel = verdict_from_legacy_coverage_projection(
        compile_loop_contract("loop_refund", compiled_spec),
        run_id="run_refund",
        coverage_projection=coverage,
        raw_verdict=raw_verdict,
    )
    return legacy["status"], kernel.status


def test_verdict_engine_matches_legacy_for_missing_required_evidence(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec()
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "missing", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "covered", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ]
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_matches_legacy_for_blocking_coverage(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec()
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "covered", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "blocked", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ]
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.BLOCKED


def test_verdict_engine_matches_legacy_for_managed_residual_risk(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec()
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "covered", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "covered", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ],
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "Manual billing export remains a visible follow-up.",
        },
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.PASSED_WITH_RESIDUAL_RISK


def test_verdict_engine_matches_legacy_for_unmanaged_residual_risk(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec()
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "covered", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "covered", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ],
        latest_gatekeeper={"id": "ev_gatekeeper", "result": "passed", "residual_risk": "Some risk remains."},
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_matches_legacy_for_disallowed_residual_risk(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec(residual_risk="Do not accept residual risk.")
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "covered", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "covered", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ],
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "Manual billing export remains a visible follow-up.",
        },
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.CONTINUE_REQUIRED


def test_verdict_engine_ignores_superseded_historical_risk_after_clean_gatekeeper_pass(tmp_path: Path) -> None:
    compiled_spec = _base_compiled_spec()
    coverage = _coverage_payload(
        [
            _target("done_when.permission", "Permission proof", "covered", required=True),
            _target("fake_done.risk_001", "Refund without audit trail.", "covered", required=False),
            _target("gatekeeper.finish", "GateKeeper finish", "covered", required=True),
        ],
        risk_signals=["Earlier blocker was resolved by the latest Builder pass."],
        latest_gatekeeper={
            "id": "ev_gatekeeper",
            "result": "passed",
            "residual_risk": "No blocking residual risk was reported by GateKeeper.",
        },
    )

    legacy_status, kernel_status = _legacy_and_kernel_statuses(
        tmp_path,
        compiled_spec=compiled_spec,
        coverage=coverage,
        raw_verdict={"passed": True},
    )

    assert LEGACY_TO_KERNEL_STATUS[legacy_status] == kernel_status == VerdictStatus.PASSED
