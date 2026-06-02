from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_accepts_gatekeeper_target_report_with_supporting_related_evidence(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "Inspector verified the target evidence.",
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
                "claim": "GateKeeper marked the target covered from the supporting inspection.",
                "verifies": ["target:done_when.check_001:covered"],
                "related_evidence_ids": ["ev_supporting"],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert targets["done_when.check_001"]["status"] == "covered"
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_supporting"]
    assert targets["done_when.check_001"]["artifact_refs"][0]["label"] == "proof-file:tests/evidence/proof.json"


def test_coverage_treats_proven_result_status_as_positive_alias(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "Inspector verified the target evidence.",
                "verifies": ["target:done_when.check_001:covered"],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper used the task verdict bucket word in coverage_results.",
                "verifies": ["evidence:ev_supporting"],
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "proven",
                        "evidence_refs": ["ev_supporting"],
                        "note": "Proven is accepted as a positive alias but projected as covered.",
                    }
                ],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "covered"
    assert targets["done_when.check_001"]["status"] == "covered"
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_supporting"]
