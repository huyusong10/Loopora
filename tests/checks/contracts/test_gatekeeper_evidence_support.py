from __future__ import annotations

from pathlib import Path

from loopora.service_runner_support import ServiceRunnerSupportMixin


def test_gatekeeper_output_rejects_string_measured_evidence_as_supporting_ref() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Builder measured this.",
            "composite_score": 1.0,
            "evidence_refs": ["builder_ev"],
            "evidence_claims": ["A concrete claim that incorrectly treats string measured evidence as proof."],
        },
        evidence_context={
            "items": [
                {
                    "id": "builder_ev",
                    "archetype": "builder",
                    "evidence_kind": "handoff",
                    "result": "completed",
                    "measured_evidence": "true",
                    "artifact_refs": [],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]


def test_gatekeeper_output_rejects_blocked_upstream_refs_as_supporting_evidence() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "Looks good.",
            "composite_score": 1.0,
            "evidence_refs": ["blocked_ev"],
            "evidence_claims": ["A concrete claim that incorrectly treats blocked evidence as support."],
            "metric_scores": {
                "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
            },
        },
        evidence_context={"items": [{"id": "blocked_ev", "archetype": "inspector", "result": "blocked"}]},
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]


def test_gatekeeper_output_rejects_plain_builder_handoff_as_supporting_evidence() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Builder says the task is done.",
            "composite_score": 1.0,
            "evidence_refs": ["builder_ev"],
            "evidence_claims": ["A concrete claim that incorrectly treats Builder self-report as proof."],
        },
        evidence_context={
            "items": [
                {
                    "id": "builder_ev",
                    "archetype": "builder",
                    "evidence_kind": "handoff",
                    "result": "completed",
                    "artifact_refs": [],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]


def test_gatekeeper_output_rejects_plain_inspector_observation_as_supporting_evidence() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Inspector says the task is done.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["A concrete claim that incorrectly treats reviewer self-report as proof."],
        },
        evidence_context={
            "items": [
                {
                    "id": "inspector_ev",
                    "archetype": "inspector",
                    "evidence_kind": "inspection",
                    "result": "passed",
                    "artifact_refs": [],
                    "verifies": [],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]


def test_gatekeeper_output_allows_inspector_structured_check_as_supporting_evidence() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Inspector ran a structured proof check.",
            "composite_score": 1.0,
            "evidence_refs": ["inspector_ev"],
            "evidence_claims": ["The structured inspection check verified the required proof boundary."],
        },
        evidence_context={
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
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["inspector_ev"]


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
        evidence_context={
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
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
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
        evidence_context={
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
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
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
        evidence_context={
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
        },
        current_evidence_id="ev_gatekeeper",
        compiled_spec={"residual_risk": "No residual risk is acceptable; any remaining risk must fail closed."},
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
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
        evidence_context={
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
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"][0].startswith("gatekeeper_pass_has_unmanaged_residual_risk:")
    assert "No blocking residual risk except untested billing export." in output["blocking_issues"][0]
    assert output["residual_risks"] == ["No blocking residual risk except untested billing export."]


def test_gatekeeper_output_allows_measured_self_evidence_with_plain_builder_context() -> None:
    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Builder handoff is visible, but GateKeeper also measured the result.",
            "composite_score": 1.0,
            "evidence_refs": ["builder_ev"],
            "evidence_claims": ["Measured GateKeeper evidence independently satisfied the pass threshold."],
            "metric_scores": {
                "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
            },
        },
        evidence_context={
            "items": [
                {
                    "id": "builder_ev",
                    "archetype": "builder",
                    "evidence_kind": "handoff",
                    "result": "completed",
                    "artifact_refs": [],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["builder_ev", "ev_gatekeeper"]


def test_gatekeeper_output_allows_builder_proof_artifact_as_supporting_evidence(tmp_path: Path) -> None:
    proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")

    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Builder left a proof artifact.",
            "composite_score": 1.0,
            "evidence_refs": ["builder_ev"],
            "evidence_claims": ["The proof artifact is available for downstream review."],
        },
        evidence_context={
            "items": [
                {
                    "id": "builder_ev",
                    "archetype": "builder",
                    "evidence_kind": "handoff",
                    "result": "completed",
                    "artifact_refs": [
                        {
                            "kind": "workspace",
                            "label": "proof-file:tests/evidence/proof.json",
                            "relative_path": "tests/evidence/proof.json",
                            "workspace_path": "tests/evidence/proof.json",
                            "absolute_path": str(proof_path),
                        }
                    ],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["builder_ev"]


def test_gatekeeper_output_rejects_missing_builder_proof_artifact_as_supporting_evidence(tmp_path: Path) -> None:
    missing_proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"

    output = ServiceRunnerSupportMixin()._coerce_gatekeeper_output(
        {
            "passed": True,
            "decision_summary": "The Builder cited a proof artifact that is no longer available.",
            "composite_score": 1.0,
            "evidence_refs": ["builder_ev"],
            "evidence_claims": ["The proof artifact path should still be readable before GateKeeper closes."],
        },
        evidence_context={
            "items": [
                {
                    "id": "builder_ev",
                    "archetype": "builder",
                    "evidence_kind": "handoff",
                    "result": "completed",
                    "artifact_refs": [
                        {
                            "kind": "workspace",
                            "label": "proof-file:tests/evidence/proof.json",
                            "relative_path": "tests/evidence/proof.json",
                            "workspace_path": "tests/evidence/proof.json",
                            "absolute_path": str(missing_proof_path),
                        }
                    ],
                }
            ]
        },
        current_evidence_id="ev_gatekeeper",
    )

    assert output["passed"] is False
    assert output["composite_score"] == 0.89
    assert output["evidence_gate_status"] == "blocked"
    assert output["blocking_issues"] == ["gatekeeper_pass_refs_not_supporting_evidence"]
