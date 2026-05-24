from __future__ import annotations

from loopora.cli_agent_plan_repair_hints import validation_repair_hints


def test_plan_repair_hints_project_host_message_categories_into_runnable_surfaces() -> None:
    hints = validation_repair_hints(
        "agent-first candidate must project host Agent success criteria into runnable surfaces: "
        "missing API compatibility, rollback proof"
    )

    assert hints == [
        "add these missing success criteria categories from --message to runnable plan surfaces: API compatibility, rollback proof",
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, evidence preferences, and GateKeeper closure",
    ]


def test_plan_repair_hints_explain_common_semantic_lint_issues() -> None:
    hints = validation_repair_hints(
        "bundle semantic lint failed: spec must include at least one Done When bullet; "
        "workflow.collaboration_intent must explain evidence flow"
    )

    assert "add # Done When bullets that make the task judgment reviewable and runnable" in hints
    assert "rewrite workflow.collaboration_intent to name evidence flow" in hints[1]
