from __future__ import annotations

from gatekeeper_output_supporting_refs_test_support import (
    assert_blocked_supporting_refs,
    builder_handoff,
    coerce_gatekeeper_pass,
    inspector_observation,
)


def test_gatekeeper_output_rejects_string_measured_evidence_as_supporting_ref() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["builder_ev"],
        evidence_items=[builder_handoff(measured_evidence="true")],
        evidence_claims=["A concrete claim that incorrectly treats string measured evidence as proof."],
        decision_summary="The Builder measured this.",
    )

    assert output["passed"] is False
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]


def test_gatekeeper_output_rejects_blocked_upstream_refs_as_supporting_evidence() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["blocked_ev"],
        evidence_items=[inspector_observation(evidence_id="blocked_ev", result="blocked")],
        evidence_claims=["A concrete claim that incorrectly treats blocked evidence as support."],
        decision_summary="Looks good.",
        metric_scores={"quality_score": {"value": 1.0, "threshold": 0.9, "passed": True}},
    )

    assert_blocked_supporting_refs(output)


def test_gatekeeper_output_rejects_plain_builder_handoff_as_supporting_evidence() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["builder_ev"],
        evidence_items=[builder_handoff()],
        evidence_claims=["A concrete claim that incorrectly treats Builder self-report as proof."],
        decision_summary="The Builder says the task is done.",
    )

    assert_blocked_supporting_refs(output)


def test_gatekeeper_output_rejects_plain_inspector_observation_as_supporting_evidence() -> None:
    output = coerce_gatekeeper_pass(
        evidence_refs=["inspector_ev"],
        evidence_items=[inspector_observation()],
        evidence_claims=["A concrete claim that incorrectly treats reviewer self-report as proof."],
        decision_summary="The Inspector says the task is done.",
    )

    assert_blocked_supporting_refs(output)
