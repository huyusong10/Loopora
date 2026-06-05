from __future__ import annotations

from pathlib import Path

from loopora.task_verdicts import build_task_verdict
from task_verdict_test_support import write_task_verdict_coverage


def test_task_verdict_bucket_artifact_refs_are_deduped(tmp_path: Path) -> None:
    proof_ref = {
        "kind": "workspace",
        "label": "proof-file:proof.json",
        "relative_path": "proof.json",
        "workspace_path": "proof.json",
        "absolute_path": str(tmp_path / "proof.json"),
    }
    run_dir = tmp_path / "run_deduped_artifact_refs"
    write_task_verdict_coverage(
        run_dir,
        {
            "summary": {"reason": "Required evidence is covered."},
            "targets": [
                {
                    "id": "done_when.check_001",
                    "label": "Required proof",
                    "status": "covered",
                    "required": True,
                    "artifact_refs": [proof_ref, dict(proof_ref)],
                },
                {
                    "id": "gatekeeper.finish",
                    "label": "GateKeeper finish",
                    "status": "covered",
                    "required": True,
                    "artifact_refs": [dict(proof_ref)],
                },
            ],
            "risk_signals": [],
        },
    )

    task_verdict = build_task_verdict(
        {
            "status": "succeeded",
            "last_verdict_json": {
                "passed": True,
                "decision_summary": "GateKeeper passed from deduped proof artifacts.",
            },
        },
        run_dir=run_dir,
    )

    proven_by_id = {item["id"]: item for item in task_verdict["buckets"]["proven"]}
    assert proven_by_id["done_when.check_001"]["artifact_refs"] == [proof_ref]
    assert proven_by_id["gatekeeper.finish"]["artifact_refs"] == [proof_ref]
