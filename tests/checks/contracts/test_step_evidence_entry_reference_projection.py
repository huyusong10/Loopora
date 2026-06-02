from __future__ import annotations

from pathlib import Path

from loopora.context_step_results import (
    StepEvidenceEntryRequest,
    StepResultContext,
    build_step_evidence_entry,
)
from loopora.run_artifacts import RunArtifactLayout


def test_step_evidence_entry_deduplicates_related_and_coverage_refs(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    result = StepResultContext(
        layout=layout,
        iter_id=0,
        step={"id": "gatekeeper_step"},
        step_order=3,
        role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        runtime_role="gatekeeper",
        output={
            "passed": False,
            "decision_summary": "Known evidence still blocks the task.",
            "evidence_refs": ["ev_builder", "ev_inspector", "ev_builder", "ev_000_03_gatekeeper_step"],
            "coverage_results": [
                {
                    "target_id": "done_when.check_001",
                    "status": "blocked",
                    "evidence_refs": ["ev_inspector", "ev_builder", "ev_inspector"],
                    "note": "The primary flow is still blocked.",
                }
            ],
        },
    )

    entry = build_step_evidence_entry(
        StepEvidenceEntryRequest(
            result=result,
            handoff={"status": "blocked", "summary": "GateKeeper blocked the task.", "artifact_refs": []},
        )
    )

    assert entry["related_evidence_ids"] == ["ev_builder", "ev_inspector"]
    assert entry["coverage_results"][0]["evidence_refs"] == ["ev_inspector", "ev_builder"]
