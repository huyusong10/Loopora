from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_blocked_target_keeps_blocker_ref_when_it_cites_supporting_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting_inspector",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "Inspector verified this target before GateKeeper found a blocker.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "blocked",
                "claim": "GateKeeper blocked the target while citing the relevant upstream evidence.",
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "blocked",
                        "evidence_refs": ["ev_supporting_inspector"],
                        "note": "The target still lacks another required proof dimension.",
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
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_supporting_inspector", "ev_gatekeeper"]
    assert projection["top_gaps"][0]["evidence_refs"] == ["ev_supporting_inspector", "ev_gatekeeper"]
