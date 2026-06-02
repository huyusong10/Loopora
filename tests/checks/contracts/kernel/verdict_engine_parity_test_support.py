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


def base_compiled_spec(*, residual_risk: object = None) -> dict:
    spec = {
        "goal": "Prove refund safety.",
        "checks": [{"id": "permission", "title": "Permission proof"}],
        "fake_done_states": ["Refund without audit trail."],
    }
    if residual_risk is not None:
        spec["residual_risk"] = residual_risk
    return spec


def coverage_payload(
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


def target(target_id: str, label: str, status: str, *, required: bool) -> dict:
    return {
        "id": target_id,
        "label": label,
        "status": status,
        "required": required,
        "evidence_refs": ["ev_support"] if status == "covered" else [],
    }


def refund_targets(
    *,
    permission_status: str = "covered",
    fake_done_status: str = "covered",
    gatekeeper_status: str = "covered",
) -> list[dict]:
    return [
        target("done_when.permission", "Permission proof", permission_status, required=True),
        target("fake_done.risk_001", "Refund without audit trail.", fake_done_status, required=False),
        target("gatekeeper.finish", "GateKeeper finish", gatekeeper_status, required=True),
    ]


def legacy_and_kernel_statuses(
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
