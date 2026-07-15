from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.runner_gatekeeper_output_validation import BLOCKED_GATEKEEPER_COMPOSITE_SCORE
from loopora.service_app import ServiceRunnerSupportMixin


PASSING_METRIC_SCORES = {
    "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
}
BLOCKED_SUPPORTING_REF_COMPOSITE_SCORE = BLOCKED_GATEKEEPER_COMPOSITE_SCORE


def coerce_gatekeeper_pass(
    *,
    evidence_refs: list[str],
    evidence_items: list[dict[str, Any]],
    evidence_claims: list[str],
    decision_summary: str = "GateKeeper found enough proof.",
    metric_scores: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "passed": True,
        "decision_summary": decision_summary,
        "composite_score": 1.0,
        "evidence_refs": evidence_refs,
        "evidence_claims": evidence_claims,
    }
    if metric_scores is not None:
        output["metric_scores"] = metric_scores
    return ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        output,
        evidence_context={"items": evidence_items},
        current_evidence_id="ev_gatekeeper",
    )


def builder_handoff(
    *,
    evidence_id: str = "builder_ev",
    artifact_refs: list[dict[str, Any]] | None = None,
    measured_evidence: Any | None = None,
    result: str = "completed",
) -> dict[str, Any]:
    item = {
        "id": evidence_id,
        "archetype": "builder",
        "evidence_kind": "handoff",
        "result": result,
        "artifact_refs": list(artifact_refs or []),
    }
    if measured_evidence is not None:
        item["measured_evidence"] = measured_evidence
    return item


def inspector_observation(
    *,
    evidence_id: str = "inspector_ev",
    verifies: list[str] | None = None,
    result: str = "passed",
) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "archetype": "inspector",
        "evidence_kind": "inspection",
        "result": result,
        "artifact_refs": [],
        "verifies": list(verifies or []),
    }


def proof_artifact(absolute_path: Path) -> dict[str, str]:
    return {
        "kind": "workspace",
        "label": "proof-file:tests/evidence/proof.json",
        "relative_path": "tests/evidence/proof.json",
        "workspace_path": "tests/evidence/proof.json",
        "absolute_path": str(absolute_path),
    }


def assert_blocked_supporting_refs(output: dict[str, Any]) -> None:
    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_SUPPORTING_REF_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]
