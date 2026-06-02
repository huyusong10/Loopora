from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


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
