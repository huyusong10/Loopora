from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_json, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_results_keep_support_refs_scoped_to_each_target(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    proof_path = tmp_path / "project" / "tests" / "evidence" / "proof.json"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text('{"ok": true}\n', encoding="utf-8")
    _write_json(
        layout.contract_compiled_spec_path,
        {
            "checks": [
                {"id": "check_001", "title": "Target A", "details": "Target A has proof."},
                {"id": "check_002", "title": "Target B", "details": "Target B still lacks proof."},
            ]
        },
    )
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_supporting",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "Inspector verified only target A.",
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
                "claim": "GateKeeper reported two targets but cited proof for only one.",
                "verifies": [
                    "target:done_when.check_001:covered",
                    "target:done_when.check_002:covered",
                    "evidence:ev_supporting",
                ],
                "related_evidence_ids": ["ev_supporting"],
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "covered",
                        "evidence_refs": ["ev_supporting"],
                        "note": "Target A is backed by the inspector proof.",
                    },
                    {
                        "target_id": "done_when.check_002",
                        "status": "covered",
                        "evidence_refs": [],
                        "note": "Target B was reported without proof.",
                    },
                ],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert projection["status"] == "partial"
    assert targets["done_when.check_001"]["status"] == "covered"
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_supporting"]
    assert targets["done_when.check_001"]["artifact_refs"][0]["label"] == "proof-file:tests/evidence/proof.json"
    assert targets["done_when.check_002"]["status"] == "weak"
    assert targets["done_when.check_002"]["reason"] == "Coverage was reported as positive without supporting evidence."
    assert targets["done_when.check_002"]["evidence_refs"] == ["ev_gatekeeper"]
    assert targets["done_when.check_002"]["artifact_refs"] == []
