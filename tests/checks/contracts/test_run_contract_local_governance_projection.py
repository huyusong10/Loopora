from __future__ import annotations

import json
from pathlib import Path

from loopora.run_artifacts import RunArtifactLayout
from loopora.run_takeaways import build_judgment_contract
from run_contract_snapshot_test_support import build_contract_snapshot


def test_run_contract_does_not_freeze_summary_only_local_governance(tmp_path: Path) -> None:
    contract = build_contract_snapshot(
        tmp_path,
        "run_prompt_summary_only_governance",
        strategy_source={
            "preset": "custom",
            "collaboration_intent": "Use the handoff and evidence flow before GateKeeper closure.",
            "roles": [
                {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [],
        },
        collaboration_summary=(
            "Future iterations stay anchored to the contract. Builder reads AGENTS.md, Inspector verifies "
            "design/ and tests/, and GateKeeper treats skipped AGENTS.md responsibilities as Blocking."
        ),
    )

    assert contract["local_governance"] == []


def test_judgment_contract_preserves_empty_runtime_local_governance(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_prompt_empty_governance_takeaway")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "contract_path": "contract/run_contract.json",
                "completion_mode": "gatekeeper",
                "compiled_spec": {
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}],
                    "coverage_targets": [{"id": "done_when.check_001", "required": True}],
                    "raw_sections": {},
                },
                "workflow": {"preset": "custom", "collaboration_intent": "Keep evidence moving."},
                "collaboration_summary": (
                    "Builder reads AGENTS.md, Inspector verifies design/ and tests/, and GateKeeper treats "
                    "skipped AGENTS.md responsibilities as Blocking."
                ),
                "local_governance": [],
                "role_postures": [
                    {
                        "role_id": "builder",
                        "role_name": "Builder",
                        "archetype": "builder",
                        "posture_notes": "Treat project-local rules as part of the task evidence.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    judgment_contract = build_judgment_contract({"runs_dir": str(layout.run_dir)})

    assert judgment_contract["local_governance"] == []
    assert judgment_contract["contract_path"] == "contract/run_contract.json"
    assert judgment_contract["check_mode"] == "specified"
    assert judgment_contract["check_count"] == 1
    assert judgment_contract["completion_mode"] == "gatekeeper"
    assert judgment_contract["strategy_preset"] == "custom"
    assert "workflow_preset" not in judgment_contract
    assert judgment_contract["coverage_targets"] == [{"id": "done_when.check_001", "required": True}]
    assert judgment_contract["role_postures"] == [
        "Builder: Treat project-local rules as part of the task evidence."
    ]
