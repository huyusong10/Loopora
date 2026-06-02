from __future__ import annotations

from pathlib import Path

from loopora.evidence_manifest import build_evidence_manifest_projection
from loopora.run_artifacts import RunArtifactLayout

from evidence_manifest_test_support import write_json, write_ledger

RUN_ID = "run_manifest"
TARGET_ID = "done_when.check_001"
TARGET_LABEL = "Required proof"
SUPPORTING_EVIDENCE_ID = "ev_supporting"


def initialized_manifest_layout(tmp_path: Path) -> RunArtifactLayout:
    layout = RunArtifactLayout(tmp_path / RUN_ID)
    layout.initialize()
    write_json(layout.run_contract_path, {"completion_mode": "gatekeeper"})
    return layout


def workspace_proof_ref(tmp_path: Path, name: str, **extra: object) -> dict:
    workspace_path = f"tests/evidence/{name}"
    return {
        "kind": "workspace",
        "label": f"proof-file:{workspace_path}",
        "relative_path": workspace_path,
        "workspace_path": workspace_path,
        "absolute_path": str(tmp_path / "project" / workspace_path),
        "exists": True,
        **extra,
    }


def gatekeeper_role_output_ref(tmp_path: Path) -> dict:
    output_path = "iterations/iter_000/steps/01__gatekeeper/output.json"
    run_relative_path = f".loopora/runs/{RUN_ID}/{output_path}"
    return {
        "kind": "role-output",
        "label": "gatekeeper-output",
        "relative_path": run_relative_path,
        "workspace_path": run_relative_path,
        "absolute_path": str(tmp_path / RUN_ID / output_path),
    }


def write_covered_target(layout: RunArtifactLayout, artifact_ref: dict) -> None:
    write_json(
        layout.evidence_coverage_path,
        {
            "schema_version": 1,
            "targets": [
                {
                    "id": TARGET_ID,
                    "kind": "done_when",
                    "label": TARGET_LABEL,
                    "status": "covered",
                    "required": True,
                    "evidence_refs": [SUPPORTING_EVIDENCE_ID],
                    "artifact_refs": [artifact_ref],
                }
            ],
        },
    )


def test_manifest_target_index_prioritizes_coverage_target_artifacts(tmp_path: Path) -> None:
    layout = initialized_manifest_layout(tmp_path)
    proof_ref = workspace_proof_ref(tmp_path, "proof.json")
    write_covered_target(layout, proof_ref)
    write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": SUPPORTING_EVIDENCE_ID,
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "source": "check_execution",
                "method": "inspection",
                "result": "passed",
                "claim": "Inspector left the proof artifact.",
                "verifies": [],
                "related_evidence_ids": [],
                "artifact_refs": [proof_ref],
            },
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "source": "verdict",
                "method": "gatekeeper_verdict",
                "result": "passed",
                "claim": "GateKeeper reported target coverage from the inspector proof.",
                "verifies": [f"target:{TARGET_ID}:covered", f"evidence:{SUPPORTING_EVIDENCE_ID}"],
                "coverage_results": [
                    {
                        "target_id": TARGET_ID,
                        "status": "covered",
                        "evidence_refs": [SUPPORTING_EVIDENCE_ID],
                        "note": "Covered by inspector proof.",
                    }
                ],
                "related_evidence_ids": [SUPPORTING_EVIDENCE_ID],
                "artifact_refs": [gatekeeper_role_output_ref(tmp_path)],
            },
        ],
    )

    manifest = build_evidence_manifest_projection(layout)

    target = manifest["targets"][0]
    assert target["claim_refs"] == ["ev_gatekeeper", SUPPORTING_EVIDENCE_ID]
    assert target["artifact_refs"][0]["label"] == "proof-file:tests/evidence/proof.json"


def test_manifest_target_index_rechecks_coverage_target_artifact_state(tmp_path: Path) -> None:
    layout = initialized_manifest_layout(tmp_path)
    missing_proof_ref = workspace_proof_ref(tmp_path, "missing.json", hash_status="sha256", sha256="stale")
    write_covered_target(layout, missing_proof_ref)
    write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": SUPPORTING_EVIDENCE_ID,
                "archetype": "inspector",
                "evidence_kind": "inspection",
                "result": "passed",
                "claim": "Inspector cited a stale coverage target artifact.",
                "artifact_refs": [],
            }
        ],
    )

    manifest = build_evidence_manifest_projection(layout)

    artifact = manifest["targets"][0]["artifact_refs"][0]
    assert artifact["label"] == "proof-file:tests/evidence/missing.json"
    assert artifact["exists"] is False
    assert artifact["hash_status"] == "missing"
    assert artifact["sha256"] == ""
