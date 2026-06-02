from __future__ import annotations

from pathlib import Path

from gatekeeper_output_supporting_refs_test_support import (
    assert_blocked_supporting_refs,
    builder_handoff,
    coerce_gatekeeper_pass,
    proof_artifact,
)


def test_gatekeeper_output_allows_builder_proof_artifact_as_supporting_evidence(tmp_path: Path) -> None:
    proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")

    output = coerce_gatekeeper_pass(
        evidence_refs=["builder_ev"],
        evidence_items=[builder_handoff(artifact_refs=[proof_artifact(proof_path)])],
        evidence_claims=["The proof artifact is available for downstream review."],
        decision_summary="The Builder left a proof artifact.",
    )

    assert output["passed"] is True
    assert output["evidence_gate_status"] == "passed"
    assert output["evidence_refs"] == ["builder_ev"]


def test_gatekeeper_output_rejects_missing_builder_proof_artifact_as_supporting_evidence(
    tmp_path: Path,
) -> None:
    missing_proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"

    output = coerce_gatekeeper_pass(
        evidence_refs=["builder_ev"],
        evidence_items=[builder_handoff(artifact_refs=[proof_artifact(missing_proof_path)])],
        evidence_claims=["The proof artifact path should still be readable before GateKeeper closes."],
        decision_summary="The Builder cited a proof artifact that is no longer available.",
    )

    assert_blocked_supporting_refs(output)
