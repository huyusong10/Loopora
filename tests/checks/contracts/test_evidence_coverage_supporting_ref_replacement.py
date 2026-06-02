from __future__ import annotations

from pathlib import Path

from evidence_coverage_test_support import _coverage_layout, _write_ledger
from loopora.evidence_coverage import build_evidence_coverage_projection


def test_coverage_replaces_historical_blocked_refs_when_supporting_evidence_covers_target(tmp_path: Path) -> None:
    layout = _coverage_layout(tmp_path)
    proof_path = tmp_path / "project" / "proof" / "primary-flow.txt"
    proof_path.parent.mkdir(parents=True)
    proof_path.write_text("primary flow proof\n", encoding="utf-8")
    _write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_old_block",
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "blocked",
                "claim": "Previous inspection blocked the target before implementation proof existed.",
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "blocked",
                        "evidence_refs": [],
                        "note": "Proof was missing in the first pass.",
                    }
                ],
            },
            {
                "id": "ev_builder_proof",
                "archetype": "builder",
                "evidence_kind": "implementation",
                "result": "completed",
                "claim": "Builder produced current project-owned proof.",
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof-file:proof/primary-flow.txt",
                        "relative_path": "proof/primary-flow.txt",
                        "workspace_path": "proof/primary-flow.txt",
                        "absolute_path": str(proof_path),
                    }
                ],
                "coverage_results": [
                    {
                        "target_id": "done_when.check_001",
                        "status": "covered",
                        "evidence_refs": [],
                        "note": "The current proof covers the primary flow.",
                    }
                ],
            },
        ],
    )

    projection = build_evidence_coverage_projection(layout)

    targets = {target["id"]: target for target in projection["targets"]}
    assert targets["done_when.check_001"]["status"] == "covered"
    assert targets["done_when.check_001"]["evidence_refs"] == ["ev_builder_proof"]
    assert targets["done_when.check_001"]["artifact_refs"][0]["label"] == "proof-file:proof/primary-flow.txt"
