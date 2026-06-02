from __future__ import annotations

from loopora.runner_gatekeeper_output_validation import BLOCKED_GATEKEEPER_COMPOSITE_SCORE
from loopora.service_runner_support import ServiceRunnerSupportMixin


def test_gatekeeper_output_rejects_unmanaged_residual_risk_on_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The proof is covered, with some residual risk.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["The structured inspection check verified the required proof boundary."],
            "residual_risks": ["Some residual risk remains."],
        },
        evidence_context=_supporting_inspector_context(),
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"][0].startswith("gatekeeper_pass_has_unmanaged_residual_risk:")
    assert "Some residual risk remains." in output["blocking_issues"][0]
    assert "owner, follow-up, or acceptance path" in output["feedback_to_builder"]
    assert output["residual_risks"] == ["Some residual risk remains."]


def test_gatekeeper_output_rejects_manual_visible_residual_risk_without_management_on_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The proof is covered, but a manual risk remains visible.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["The structured inspection check verified the required proof boundary."],
            "residual_risks": ["Ownerless manual billing export remains visible."],
        },
        evidence_context=_supporting_inspector_context(),
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"][0].startswith("gatekeeper_pass_has_unmanaged_residual_risk:")
    assert "Ownerless manual billing export remains visible." in output["blocking_issues"][0]
    assert output["residual_risks"] == ["Ownerless manual billing export remains visible."]


def test_gatekeeper_output_rejects_residual_risk_when_contract_disallows_acceptance_on_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The proof is covered, with an accepted follow-up risk.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["The structured inspection check verified the required proof boundary."],
            "residual_risks": ["Manual billing export remains visible as a follow-up owned by Support."],
        },
        evidence_context=_supporting_inspector_context(),
        current_evidence_id="ev_gatekeeper",
        compiled_spec={"residual_risk": "No residual risk is acceptable; any remaining risk must fail closed."},
    )

    assert output["passed"] is False
    assert output["composite_score"] == BLOCKED_GATEKEEPER_COMPOSITE_SCORE
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"][0].startswith("gatekeeper_pass_violates_no_residual_risk_policy:")
    assert "Manual billing export remains visible as a follow-up owned by Support." in output["blocking_issues"][0]
    assert output["residual_risks"] == ["Manual billing export remains visible as a follow-up owned by Support."]


def test_gatekeeper_output_rejects_negated_residual_risk_with_exception_on_pass() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The proof is covered, with an exception hidden behind no blocking residual risk wording.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["The structured inspection check verified the required proof boundary."],
            "residual_risks": ["No blocking residual risk except untested billing export."],
        },
        evidence_context=_supporting_inspector_context(),
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"][0].startswith("gatekeeper_pass_has_unmanaged_residual_risk:")
    assert "No blocking residual risk except untested billing export." in output["blocking_issues"][0]
    assert output["residual_risks"] == ["No blocking residual risk except untested billing export."]


def _supporting_inspector_context() -> dict:
    return {
        "items": [
            {
                "id": "inspector_ev",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "artifact_refs": [],
                "verifies": ["check_results:required_proof:passed"],
            }
        ]
    }
