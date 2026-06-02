from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopora.task_verdicts import build_task_verdict


def write_task_verdict_coverage(run_dir: Path, payload: dict) -> None:
    coverage_path = run_dir / "evidence" / "coverage.json"
    coverage_path.parent.mkdir(parents=True)
    coverage_payload = {"schema_version": 1, **payload}
    coverage_path.write_text(json.dumps(coverage_payload, ensure_ascii=False), encoding="utf-8")


def task_verdict_coverage_target(
    target_id: str,
    label: str,
    *,
    status: str,
    required: object = True,
    reason: str = "",
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "id": target_id,
        "label": label,
        "status": status,
        "required": required,
    }
    if reason:
        target["reason"] = reason
    return target


def required_proof_target(
    *,
    status: str = "covered",
    required: object = True,
    kind: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    target = task_verdict_coverage_target(
        "done_when.check_001",
        "Required proof",
        status=status,
        required=required,
        reason=reason,
    )
    if kind is not None:
        target["kind"] = kind
    return target


def gatekeeper_finish_target(
    *,
    status: str = "covered",
    required: object = True,
    kind: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    target = task_verdict_coverage_target(
        "gatekeeper.finish",
        "GateKeeper finish",
        status=status,
        required=required,
        reason=reason,
    )
    if kind is not None:
        target["kind"] = kind
    return target


def write_task_verdict_covered_gatekeeper_coverage(
    run_dir: Path,
    *,
    latest_gatekeeper: dict | None = None,
    risk_signals: list[str] | None = None,
    summary_reason: str = "Required evidence is covered.",
) -> None:
    payload = {
        "summary": {"reason": summary_reason},
        "targets": [
            required_proof_target(),
            gatekeeper_finish_target(),
        ],
        "risk_signals": list(risk_signals or []),
    }
    if latest_gatekeeper is not None:
        payload["latest_gatekeeper"] = latest_gatekeeper
    write_task_verdict_coverage(run_dir, payload)


def build_passed_task_verdict(
    run_dir: Path,
    *,
    residual_risks: list[str] | None = None,
    compiled_residual_risk: str | None = None,
    decision_summary: str = "GateKeeper passed.",
    verdict_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run = {
        "status": "succeeded",
        "last_verdict_json": {
            "passed": True,
            "decision_summary": decision_summary,
        },
    }
    if residual_risks is not None:
        run["last_verdict_json"]["residual_risks"] = residual_risks
    if verdict_updates is not None:
        run["last_verdict_json"].update(verdict_updates)
    if compiled_residual_risk is not None:
        run["compiled_spec_json"] = {"residual_risk": compiled_residual_risk}
    return build_task_verdict(run, run_dir=run_dir)


def gatekeeper_pass_evidence(
    *,
    evidence_refs: list[str] | None = None,
    supporting_evidence_refs: list[str] | None = None,
    non_supporting_evidence_refs: list[str] | None = None,
    residual_risk: str = "",
) -> dict[str, Any]:
    gatekeeper: dict[str, Any] = {
        "id": "ev_gatekeeper",
        "result": "passed",
        "residual_risk": residual_risk,
    }
    if evidence_refs is not None:
        gatekeeper["evidence_refs"] = evidence_refs
    if supporting_evidence_refs is not None:
        gatekeeper["supporting_evidence_refs"] = supporting_evidence_refs
    if non_supporting_evidence_refs is not None:
        gatekeeper["non_supporting_evidence_refs"] = non_supporting_evidence_refs
    return gatekeeper


def gatekeeper_residual_risk(residual_risk: str) -> dict[str, Any]:
    return gatekeeper_pass_evidence(residual_risk=residual_risk)
