from __future__ import annotations

from gatekeeper_output_supporting_refs_test_support import (
    PASSING_METRIC_SCORES,
    builder_handoff,
    coerce_gatekeeper_pass,
    inspector_observation,
)


def test_gatekeeper_output_allows_inspector_structured_check_as_supporting_evidence() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["inspector_ev"],
        evidence_items=[inspector_observation(verifies=["check_results:required_proof:passed"])],
        evidence_claims=["The structured inspection check verified the required proof boundary."],
        decision_summary="The Inspector ran a structured proof check.",
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["inspector_ev"]


def test_gatekeeper_output_allows_measured_self_evidence_with_plain_builder_context() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["builder_ev"],
        evidence_items=[builder_handoff()],
        evidence_claims=["Measured GateKeeper evidence independently satisfied the pass threshold."],
        decision_summary="The Builder handoff is visible, but GateKeeper also measured the result.",
        metric_scores=PASSING_METRIC_SCORES,
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["builder_ev", "ev_gatekeeper"]
