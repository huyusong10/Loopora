from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_downgrades_positive_target_report_without_supporting_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper marked the target covered without supporting refs.",
                "verifies": ["target:done_when.check_001:covered"],
                "related_evidence_ids": [],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert targets["done_when.check_001"]["status"] == "weak"
    assert targets["done_when.check_001"]["reason"] == "Coverage was reported as positive without supporting evidence."
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_gatekeeper"]


def test_coverage_keeps_blocked_target_when_later_positive_report_lacks_support(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_inspector",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "blocked",
                "claim": "Inspector blocked the required target.",
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "blocked",
                        "evidence_refs": [],
                        "note": "Direct proof is missing.",
                    }
                ],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "blocked",
                "claim": "GateKeeper attempted positive target coverage from blocked evidence.",
                "measured_evidence": True,
                "concrete_evidence_claim_count": 1,
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "covered",
                        "evidence_refs": ["ev_inspector"],
                        "note": "This ref is not supporting evidence.",
                    }
                ],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "blocked"
    assert targets["done_when.check_001"]["status"] == "blocked"
    assert targets["done_when.check_001"]["reason"] == "Evidence reported this coverage target as blocked or failed."
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_inspector", "ev_gatekeeper"]


def test_coverage_result_missing_remains_gap_instead_of_blocker(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_inspector",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "completed",
                "claim": "Inspector reported the required target still has no direct proof.",
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "missing",
                        "evidence_refs": [],
                        "note": "No current proof covers this target yet.",
                    }
                ],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert projection["blocked_target_count"] == 0
    assert targets["done_when.check_001"]["status"] == "missing"
    assert targets["done_when.check_001"]["reason"] == "Evidence reported this coverage target is still missing."
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_inspector"]
    assert projection["top_gaps"][0]["status"] == "missing"
