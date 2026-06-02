from __future__ import annotations

import json
from pathlib import Path

from loopora.run_artifacts import RunArtifactLayout
from loopora.runner_step_context_inputs import manifest_prompt_context


def test_manifest_prompt_context_does_not_promote_string_booleans(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt")
    layout.initialize()
    (layout.evidence_manifest_path).write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "id": "ev_string_bool",
                        "verification_status": "direct_proof",
                        "measured_evidence": "true",
                        "concrete_evidence_claim_count": True,
                        "artifact_count": 1,
                        "artifact_backed": "true",
                        "workspace_backed": "true",
                        "reproducible": "true",
                        "coverage_targets": [
                            {
                                "id": "done_when.check",
                                "kind": "done_when",
                                "label": "Done check",
                                "reported_status": "covered",
                                "coverage_status": "covered",
                                "required": "true",
                                "evidence_refs": ["ev_support"],
                            },
                            {
                                "id": "evidence_preference.pref_001",
                                "kind": "evidence_preference",
                                "label": "Evidence preference",
                                "reported_status": "weak",
                                "coverage_status": "weak",
                                "required": "true",
                                "evidence_refs": [],
                            },
                            "gatekeeper.finish",
                        ],
                    }
                ],
                "problems": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _summary, claims = manifest_prompt_context(layout, ["ev_string_bool"])

    assert claims[0]["measured_evidence"] is False
    assert claims[0]["concrete_evidence_claim_count"] == 0
    assert claims[0]["artifact_backed"] is False
    assert claims[0]["workspace_backed"] is False
    assert claims[0]["reproducible"] is False
    assert claims[0]["coverage_targets"][0] == {
        "id": "done_when.check",
        "kind": "done_when",
        "label": "Done check",
        "reported_status": "covered",
        "coverage_status": "covered",
        "required": True,
        "evidence_refs": ["ev_support"],
    }
    assert claims[0]["coverage_targets"][1]["required"] is False
    assert claims[0]["coverage_targets"][2]["id"] == "gatekeeper.finish"
    assert claims[0]["coverage_targets"][2]["required"] is True
