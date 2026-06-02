from __future__ import annotations

import json
from pathlib import Path

from loopora.run_artifacts import RunArtifactLayout
from loopora.run_takeaways import build_evidence_manifest


NORMALIZED_DIRECT_PROOF_CLAIM_COUNT = 2
NORMALIZED_MANIFEST_PROBLEM_COUNT = 2


def test_takeaway_evidence_manifest_does_not_promote_boolean_manifest_counts(tmp_path: Path) -> None:
    runs_dir = tmp_path / "run"
    layout = RunArtifactLayout(runs_dir)
    layout.initialize()
    layout.evidence_manifest_path.write_text(
        json.dumps(
            {
                "manifest_path": True,
                "claim_count": True,
                "artifact_backed_claim_count": "1",
                "direct_proof_claim_count": NORMALIZED_DIRECT_PROOF_CLAIM_COUNT,
                "problems": [
                    {"code": True, "claim_id": 7, "severity": False, "message": 3},
                    {"code": "missing_artifact", "claim_id": "ev_001", "severity": "warning", "message": "Proof file is missing."},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = build_evidence_manifest({"runs_dir": str(runs_dir)})

    assert manifest["claim_count"] == 0
    assert manifest["artifact_backed_claim_count"] == 0
    assert manifest["direct_proof_claim_count"] == NORMALIZED_DIRECT_PROOF_CLAIM_COUNT
    assert manifest["manifest_path"] == "evidence/manifest.json"
    assert manifest["problem_count"] == NORMALIZED_MANIFEST_PROBLEM_COUNT
    assert manifest["problems"][0] == {"code": "", "claim_id": "", "severity": "", "message": ""}
    assert manifest["problems"][1] == {
        "code": "missing_artifact",
        "claim_id": "ev_001",
        "severity": "warning",
        "message": "Proof file is missing.",
    }
