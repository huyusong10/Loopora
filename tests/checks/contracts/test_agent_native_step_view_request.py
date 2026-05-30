from __future__ import annotations

from loopora.agent_native_step_view import AgentNativeStepViewRequest, agent_native_step_view
from loopora.run_artifacts import RunArtifactLayout


def test_agent_native_step_view_request_consumes_step_instruction_context(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "workspace" / ".loopora" / "runs" / "run_agent_step_view")
    layout.initialize()
    step_context = {
        "iteration": {
            "coverage_status": "blocked",
            "evidence_progress_mode": "stalled",
            "target_count": 2,
            "covered_check_count": 1,
            "missing_check_count": 1,
            "missing_check_ids": ["check_002"],
            "coverage_top_gaps": [{"target_id": "done_when.check_002"}],
        },
        "evidence": {"known_ids": ["ev_000_00_builder_step"], "items": [{"id": "ev_000_00_builder_step"}]},
    }

    step_view = agent_native_step_view(
        AgentNativeStepViewRequest(
            adapter="codex",
            run={"id": "run_agent_step_view"},
            layout=layout,
            iter_id=0,
            step={"id": "builder_step", "action_policy": {}},
            step_order=0,
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
            runtime_role="builder",
            prompt="Build the smallest proof.",
            output_schema={"type": "object"},
            known_evidence_ids=["ev_000_00_builder_step"],
            step_instruction_context=step_context,
        )
    )

    assert step_view["required_coverage"]["status"] == "blocked"
    assert step_view["required_coverage"]["missing_check_ids"] == ["check_002"]
    assert step_view["known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"
