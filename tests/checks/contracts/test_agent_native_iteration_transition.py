from __future__ import annotations

from types import SimpleNamespace

from loopora.agent_native_iteration_transition import (
    AgentNativeNextIterationStateRequest,
    agent_native_next_iteration_state_update,
)
from loopora.agent_native_runtime_context import agent_native_iteration_state


CURRENT_GATEKEEPER_COMPOSITE = 0.73
NEXT_ITERATION_ID = 2
PRIOR_COMPOSITE_WITHOUT_GATEKEEPER = 0.62


def test_agent_native_iteration_state_rejects_bool_iteration_identity() -> None:
    iteration = agent_native_iteration_state({"iter_id": True})

    assert iteration.iter_id == 0


def test_agent_native_next_iteration_state_carries_previous_outputs_and_resets_current_work() -> None:
    update = agent_native_next_iteration_state_update(
        AgentNativeNextIterationStateRequest(
            iteration=SimpleNamespace(
                current_gatekeeper_result={"composite_score": CURRENT_GATEKEEPER_COMPOSITE},
                previous_composite=0.41,
                current_session_refs_by_step={"gatekeeper_step": {"session_id": "session-gatekeeper"}},
                stagnation={"stagnation_mode": "coverage_gap"},
            ),
            next_iter=NEXT_ITERATION_ID,
            previous_outputs_by_step={"builder_step": {"summary": "Built the first slice."}},
            previous_outputs_by_role={"builder": {"summary": "Built the first slice."}},
            previous_outputs_by_archetype={"builder": {"summary": "Built the first slice."}},
            previous_handoffs_by_step={"gatekeeper_step": {"status": "blocked"}},
            previous_handoffs_by_role={"gatekeeper": {"status": "blocked"}},
            previous_iteration_summary={"iter": 1, "summary": "Needs stronger proof."},
        )
    )

    assert update["iter_id"] == NEXT_ITERATION_ID
    assert update["step_index"] == 0
    assert update["previous_composite"] == CURRENT_GATEKEEPER_COMPOSITE
    assert update["previous_outputs_by_step"]["builder_step"]["summary"] == "Built the first slice."
    assert update["previous_handoffs_by_role"]["gatekeeper"]["status"] == "blocked"
    assert update["previous_iteration_summary"]["summary"] == "Needs stronger proof."
    assert update["previous_session_refs_by_step"] == {"gatekeeper_step": {"session_id": "session-gatekeeper"}}
    assert update["stagnation"] == {"stagnation_mode": "coverage_gap"}
    assert update["current_outputs_by_step"] == {}
    assert update["current_outputs_by_role"] == {}
    assert update["current_outputs_by_archetype"] == {}
    assert update["current_handoffs"] == []
    assert update["current_session_refs_by_step"] == {}
    assert update["current_gatekeeper_result"] is None
    assert update["current_guide_result"] is None
    assert update["step_results"] == []
    assert update["control_queue"] == []
    assert update["control_queue_index"] == 0
    assert update["control_queue_iter"] is None
    assert update["parallel_group_snapshot"] == {}
    assert update["active_step"] == {}


def test_agent_native_next_iteration_state_preserves_prior_composite_without_gatekeeper_score() -> None:
    update = agent_native_next_iteration_state_update(
        AgentNativeNextIterationStateRequest(
            iteration=SimpleNamespace(
                current_gatekeeper_result=None,
                previous_composite=PRIOR_COMPOSITE_WITHOUT_GATEKEEPER,
                current_session_refs_by_step={},
                stagnation={},
            ),
            next_iter=3,
            previous_outputs_by_step={},
            previous_outputs_by_role={},
            previous_outputs_by_archetype={},
            previous_handoffs_by_step={},
            previous_handoffs_by_role={},
            previous_iteration_summary=None,
        )
    )

    assert update["previous_composite"] == PRIOR_COMPOSITE_WITHOUT_GATEKEEPER
