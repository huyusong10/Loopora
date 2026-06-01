from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_accepts_gatekeeper_finish_when_pass_cites_builder_proof_artifact(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_builder",
                "archetype": "builder",
                "evidence_kind": "handoff",
                "result": "completed",
                "claim": "Builder left a proof artifact for the required target.",
                "verifies": ["target:done_when.check_001:covered"],
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof-file:tests/evidence/proof.json",
                        "relative_path": "tests/evidence/proof.json",
                        "workspace_path": "tests/evidence/proof.json",
                        "absolute_path": str(proof_path),
                    }
                ],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from the Builder proof artifact.",
                "verifies": ["evidence:ev_builder"],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "covered"
    assert targets["gatekeeper.finish"]["status"] == "covered"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_builder", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == ["ev_builder"]
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == []


def test_coverage_blocks_gatekeeper_finish_when_builder_proof_artifact_is_missing(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    missing_proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_builder",
                "archetype": "builder",
                "evidence_kind": "handoff",
                "result": "completed",
                "claim": "Builder cited a proof artifact that no longer exists.",
                "verifies": ["target:done_when.check_001:covered"],
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof-file:tests/evidence/proof.json",
                        "relative_path": "tests/evidence/proof.json",
                        "workspace_path": "tests/evidence/proof.json",
                        "absolute_path": str(missing_proof_path),
                    }
                ],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper tried to pass from a missing Builder proof artifact.",
                "verifies": ["evidence:ev_builder"],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "blocked"
    assert targets["gatekeeper.finish"]["status"] == "blocked"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_builder", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_builder"]


def test_coverage_blocks_gatekeeper_finish_when_builder_proof_artifact_lacks_absolute_path(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_builder",
                "archetype": "builder",
                "evidence_kind": "handoff",
                "result": "completed",
                "claim": "Builder cited a proof artifact without a checkable absolute path.",
                "verifies": ["target:done_when.check_001:covered"],
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof-file:tests/evidence/proof.json",
                        "relative_path": "tests/evidence/proof.json",
                        "workspace_path": "tests/evidence/proof.json",
                    }
                ],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper tried to pass from an unchecked proof artifact ref.",
                "verifies": ["evidence:ev_builder"],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "blocked"
    assert targets["gatekeeper.finish"]["status"] == "blocked"
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_builder", "ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == ["ev_builder"]


def test_coverage_ignores_explicit_no_residual_risk_markers(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed without accepted residual risk.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "None",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 0
    assert projection["risk_signals"] == []
    assert projection["latest_gatekeeper"]["residual_risk"] == "None"


def test_coverage_ignores_chinese_no_meaningful_residual_risk_marker(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed without meaningful residual risk.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "无重大残余风险",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 0
    assert projection["risk_signals"] == []
    assert projection["latest_gatekeeper"]["residual_risk"] == "无重大残余风险"


def test_coverage_keeps_residual_risk_exception_after_no_risk_phrase(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper named a managed exception.",
                "verifies": ["evidence:ev_supporting"],
                "residual_risk": "No residual risk except mobile checkout remains a Support-owned follow-up.",
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    assert projection["status"] == "covered"
    assert projection["residual_risk_count"] == 1
    assert projection["risk_signals"] == [
        "No residual risk except mobile checkout remains a Support-owned follow-up."
    ]
    assert projection["latest_gatekeeper"]["residual_risk"] == (
        "No residual risk except mobile checkout remains a Support-owned follow-up."
    )


def test_coverage_accepts_gatekeeper_finish_when_pass_has_measured_self_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_check",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from its measured benchmark result.",
                "verifies": ["evidence:ev_gatekeeper"],
                "measured_evidence": True,
                "concrete_evidence_claim_count": 1,
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "covered"
    assert targets["gatekeeper.finish"]["status"] == "covered"
    assert targets["gatekeeper.finish"]["reason"] == "GateKeeper passed with measured self evidence and concrete evidence claims."
    assert targets["gatekeeper.finish"]["evidence_refs"] == ["ev_gatekeeper"]
    assert projection["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["non_supporting_evidence_refs"] == []
    assert projection["latest_gatekeeper"]["self_measured_evidence"] is True
    assert projection["latest_gatekeeper"]["self_evidence_claim_count"] == 1


def test_coverage_does_not_accept_gatekeeper_self_ref_without_measured_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_check",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "The required proof is covered.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from a prose-only self report.",
                "verifies": ["evidence:ev_gatekeeper"],
                "measured_evidence": False,
                "concrete_evidence_claim_count": 1,
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert targets["gatekeeper.finish"]["status"] == "missing"
    assert targets["gatekeeper.finish"]["evidence_refs"] == []
    assert projection["latest_gatekeeper"]["self_measured_evidence"] is False
    assert projection["latest_gatekeeper"]["self_evidence_claim_count"] == 1


def test_coverage_does_not_accept_string_measured_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from a string-shaped measured evidence marker.",
                "verifies": ["evidence:ev_gatekeeper"],
                "measured_evidence": "true",
                "concrete_evidence_claim_count": 1,
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert targets["gatekeeper.finish"]["status"] == "missing"
    assert targets["gatekeeper.finish"]["evidence_refs"] == []
    assert projection["latest_gatekeeper"]["self_measured_evidence"] is False


def test_coverage_does_not_accept_boolean_concrete_evidence_claim_count(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from a boolean-shaped evidence claim count.",
                "verifies": ["evidence:ev_gatekeeper"],
                "measured_evidence": True,
                "concrete_evidence_claim_count": True,
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert targets["gatekeeper.finish"]["status"] == "missing"
    assert targets["gatekeeper.finish"]["evidence_refs"] == []
    assert projection["latest_gatekeeper"]["self_measured_evidence"] is False
    assert projection["latest_gatekeeper"]["self_evidence_claim_count"] == 0
