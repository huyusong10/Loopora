from __future__ import annotations

from pathlib import Path

from loopora.context_step_results import (
    StepEvidenceEntryRequest,
    StepResultContext,
    build_step_evidence_entry,
    build_step_handoff,
)
from loopora.run_artifacts import RunArtifactLayout


def test_builder_abandoned_note_is_residual_risk_not_blocking_item(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    result = StepResultContext(
        layout=layout,
        iter_id=0,
        step={"id": "builder_step"},
        step_order=0,
        role={"id": "builder", "name": "Builder", "archetype": "builder"},
        runtime_role="generator",
        output={
            "attempted": "Built the focused starter slice.",
            "abandoned": "Did not broaden the sandbox into a full application.",
            "assumption": "Inspect the starter check output before GateKeeper.",
            "summary": "Starter flow now has a project-owned check.",
            "changed_files": [],
            "proof_files": [],
            "proof_artifacts": [],
            "artifact_paths": [],
        },
    )

    handoff = build_step_handoff(result)
    evidence = build_step_evidence_entry(StepEvidenceEntryRequest(result=result, handoff=handoff))

    assert handoff["status"] == "completed"
    assert handoff["blocking_items"] == []
    assert "Out-of-scope or unfinished note: Did not broaden the sandbox into a full application." in handoff["summary"]
    assert evidence["residual_risk"] == "Did not broaden the sandbox into a full application."
    assert evidence["verifies"] == ["step_result:builder_step:completed"]


def test_inspector_handoff_deduplicates_failed_items_and_check_results(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "contract_inspection_step"},
            step_order=1,
            role={"id": "contract_inspector", "name": "Contract Inspector", "archetype": "inspector"},
            runtime_role="contract_inspector",
            output={
                "tester_observations": "Primary-flow proof is still weak.",
                "failed_items": [
                    {"id": "contract.primary_flow", "title": "Primary flow evidence"},
                    {"id": "contract.project_evidence", "title": "Project-owned evidence"},
                ],
                "check_results": [
                    {"id": "contract.primary_flow", "title": "Primary flow evidence", "status": "failed"},
                    {"id": "contract.project_evidence", "title": "Project-owned evidence", "status": "failed"},
                ],
                "dynamic_checks": [],
            },
        )
    )

    assert handoff["status"] == "blocked"
    assert handoff["blocking_items"] == ["Primary flow evidence", "Project-owned evidence"]
