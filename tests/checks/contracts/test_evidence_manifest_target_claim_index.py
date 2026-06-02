from __future__ import annotations

from pathlib import Path

from loopora.evidence_manifest import build_evidence_manifest_projection
from loopora.run_artifacts import RunArtifactLayout

from evidence_manifest_test_support import write_json, write_ledger


def test_manifest_target_index_uses_coverage_evidence_refs_for_derived_targets(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_manifest")
    layout.initialize()
    write_json(layout.run_contract_path, {"completion_mode": "gatekeeper"})
    write_json(
        layout.evidence_coverage_path,
        {
            "schema_version": 1,
            "targets": [
                {
                    "id": "gatekeeper.finish",
                    "kind": "gatekeeper",
                    "label": "GateKeeper finish",
                    "status": "covered",
                    "required": True,
                    "evidence_refs": ["ev_gatekeeper"],
                }
            ],
        },
    )
    write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "source": "verdict",
                "method": "gatekeeper_verdict",
                "result": "passed",
                "claim": "GateKeeper passed from measured self evidence.",
                "verifies": ["evidence:ev_gatekeeper"],
                "related_evidence_ids": [],
                "artifact_refs": [],
                "measured_evidence": True,
                "concrete_evidence_claim_count": 1,
            }
        ],
    )

    manifest = build_evidence_manifest_projection(layout)

    gatekeeper_claim = manifest["claims"][0]
    gatekeeper_target = manifest["targets"][0]
    assert manifest["ledger_only_claim_count"] == 1
    assert manifest["run_artifact_claim_count"] == 0
    assert gatekeeper_claim["measured_evidence"] is True
    assert gatekeeper_claim["concrete_evidence_claim_count"] == 1
    assert gatekeeper_target["claim_refs"] == ["ev_gatekeeper"]


def test_manifest_projection_preserves_intrinsic_required_targets_without_promoting_string_booleans(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_manifest")
    layout.initialize()
    write_json(layout.run_contract_path, {"completion_mode": "gatekeeper"})
    write_json(
        layout.evidence_coverage_path,
        {
            "schema_version": 1,
            "targets": [
                {
                    "id": "done_when.check",
                    "kind": "done_when",
                    "label": "Done check",
                    "status": "covered",
                    "required": "true",
                    "evidence_refs": ["ev_gatekeeper"],
                },
                {
                    "id": "gatekeeper.finish",
                    "kind": "gatekeeper",
                    "label": "GateKeeper finish",
                    "status": "covered",
                    "required": False,
                    "evidence_refs": ["ev_gatekeeper"],
                },
                {
                    "id": "evidence_preference.pref_001",
                    "kind": "evidence_preference",
                    "label": "Evidence preference",
                    "status": "weak",
                    "required": "true",
                    "evidence_refs": [],
                },
            ],
        },
    )
    write_ledger(
        layout.evidence_ledger_path,
        [
            {
                "id": "ev_gatekeeper",
                "archetype": "gatekeeper",
                "evidence_kind": "verdict",
                "result": "passed",
                "claim": "GateKeeper passed from string-shaped evidence markers.",
                "verifies": ["target:done_when.check:covered"],
                "related_evidence_ids": [],
                "artifact_refs": [],
                "measured_evidence": "true",
                "concrete_evidence_claim_count": True,
            }
        ],
    )

    manifest = build_evidence_manifest_projection(layout)

    targets_by_id = {target["id"]: target for target in manifest["targets"]}
    assert manifest["claims"][0]["measured_evidence"] is False
    assert manifest["claims"][0]["concrete_evidence_claim_count"] == 0
    assert manifest["claims"][0]["coverage_targets"][0]["required"] is True
    assert targets_by_id["done_when.check"]["required"] is True
    assert targets_by_id["gatekeeper.finish"]["required"] is True
    assert targets_by_id["evidence_preference.pref_001"]["required"] is False
