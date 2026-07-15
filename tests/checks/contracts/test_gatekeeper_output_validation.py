from __future__ import annotations

from loopora.runner_gatekeeper_output_validation import BLOCKED_GATEKEEPER_COMPOSITE_SCORE
from loopora.service_app import ServiceRunnerSupportMixin


def test_gatekeeper_output_rejects_unknown_evidence_refs() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "Looks good.",
            "composite_score": 1.0,
            "evidence_refs": ["missing_ev"],
            "evidence_claims": ["A concrete claim that still points to an unknown evidence ref."],
        },
        evidence_context={"items": [{"id": "known_ev", "archetype": "inspector"}]},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_evidence_refs_unknown: missing_ev"]


def test_gatekeeper_output_rejects_unknown_coverage_result_evidence_refs() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The top-level verdict cites real evidence, but target coverage cites an invented ref.",
            "composite_score": 1.0,
            "evidence_refs": ["known_ev"],
            "evidence_claims": ["A concrete claim that cites the known upstream inspection evidence."],
            "coverage_results": [
                {
                    "target_id": "fake_done.risk_001",
                    "status": "covered",
                    "evidence_refs": ["invented_ev"],
                    "note": "This target-specific evidence ref is not in the known evidence set.",
                }
            ],
        },
        evidence_context={
            "items": [
                {
                    "id": "known_ev",
                    "archetype": "inspector",
                    "result": "passed",
                    "verifies": ["check_results:known_ev_check:passed"],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_coverage_evidence_refs_unknown: invented_ev"]


def test_gatekeeper_output_allows_first_gate_measured_evidence_claim() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "",
            "metric_scores": {
                "quality_score": {"value": 0.95, "threshold": 0.9, "passed": True},
            },
            "evidence_claims": ["Measured benchmark evidence satisfied the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is True
    assert output["decision_summary"] == "All checks passed."
    assert output["evidence_refs"] == ["ev_gatekeeper"]
    assert output["evidence_gate_status"] == "passed"


def test_gatekeeper_output_requires_literal_boolean_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": "true",
            "decision_summary": "Looks good.",
            "metric_scores": {
                "quality_score": {"value": 0.95, "threshold": 0.9, "passed": "true"},
            },
            "evidence_claims": ["Measured benchmark evidence satisfied the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["metric_scores"]["quality_score"]["passed"] is False
    assert output["metrics"][0]["passed"] is False
    assert output["evidence_refs"] == []
    assert output["evidence_gate_status"] == "not_passed"


def test_gatekeeper_output_default_composite_requires_literal_boolean_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": "true",
            "decision_summary": "A string pass should not set the fallback score.",
            "evidence_claims": ["String boolean values are not measured proof."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.0
    assert output["evidence_gate_status"] == "not_passed"


def test_gatekeeper_output_normalizes_metric_row_booleans() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": False,
            "decision_summary": "The measured check did not pass.",
            "metrics": [
                {"name": "quality_score", "value": 0.8, "threshold": 0.9, "passed": "false"},
            ],
            "evidence_claims": ["Measured benchmark evidence did not satisfy the first GateKeeper pass."],
        },
        evidence_context={"items": []},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["metric_scores"]["quality_score"]["passed"] is False
    assert output["metrics"] == [{"name": "quality_score", "value": 0.8, "threshold": 0.9, "passed": False}]
