from __future__ import annotations

from pathlib import Path

from loopora.context_step_results import StepResultContext, build_step_handoff
from loopora.run_artifacts import RunArtifactLayout


def test_gatekeeper_handoff_projects_blocking_issues_and_hard_constraints(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()

    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step"},
            step_order=2,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            runtime_role="gatekeeper",
            output={
                "passed": False,
                "decision_summary": "Primary-flow evidence is not sufficient.",
                "feedback_to_builder": "Produce direct primary-flow proof before asking for closure.",
                "blocking_issues": ["primary_flow_unproven"],
                "hard_constraint_violations": ["audit_chain_missing"],
                "failed_check_ids": ["done_when.check_001"],
                "priority_failures": [{"summary": "Payment failure path has no traceable handoff."}],
            },
        )
    )

    assert handoff["status"] == "blocked"
    assert handoff["blocking_items"] == [
        "primary_flow_unproven",
        "audit_chain_missing",
        "done_when.check_001",
        "Payment failure path has no traceable handoff.",
    ]
    assert handoff["recommended_next_action"] == "Produce direct primary-flow proof before asking for closure."


def test_gatekeeper_pass_handoff_does_not_report_blocking_next_action(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()

    handoff = build_step_handoff(
        StepResultContext(
            layout=layout,
            iter_id=0,
            step={"id": "gatekeeper_step"},
            step_order=2,
            role={"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
            runtime_role="gatekeeper",
            output={
                "passed": True,
                "decision_summary": "Required evidence passed.",
                "feedback_to_builder": "",
                "feedback_to_generator": "",
                "blocking_issues": [],
                "hard_constraint_violations": [],
                "failed_check_ids": [],
                "priority_failures": [],
            },
        )
    )

    assert handoff["status"] == "passed"
    assert handoff["blocking_items"] == []
    assert handoff["recommended_next_action"] == "No further role action is required; the GateKeeper verdict passed."
