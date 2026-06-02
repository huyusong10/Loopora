from __future__ import annotations

from inspect import signature

from loopora.compiler import compile_loop_contract, compile_loop_strategy
from loopora.kernel.contract import ResidualRiskPolicy


STRATEGY_MAX_ITERATIONS = 4
STRATEGY_MAX_STEP_RETRIES = 2


def test_strategy_compiler_accepts_strategy_source_boundary_name() -> None:
    parameters = signature(compile_loop_strategy).parameters

    assert "strategy_source" in parameters
    assert "workflow" not in parameters


def test_compiled_spec_compiles_to_loop_contract_without_workflow_state() -> None:
    contract = compile_loop_contract(
        "loop_refund",
        {
            "goal": "Ship refund safety.",
            "checks": [{"id": "permission", "title": "Permission proof"}],
            "success_surface": ["Refunds are auditable."],
            "fake_done_states": ["Happy path only."],
            "evidence_preferences": ["Prefer contract tests."],
            "residual_risk": {"policy": "disallow"},
        },
        completion_mode="rounds",
    )

    target_ids = {target.id for target in contract.evidence_targets}
    assert contract.task == "Ship refund safety."
    assert contract.done_when[0].id == "permission"
    assert contract.evidence_needed[0].label == "Prefer contract tests."
    assert contract.residual_risk_policy == ResidualRiskPolicy.DISALLOW
    assert {
        "done_when.permission",
        "success_surface.surface_001",
        "fake_done.risk_001",
        "evidence_preference.pref_001",
    } <= target_ids
    assert "gatekeeper.finish" not in target_ids


def test_strategy_source_compiles_to_loop_strategy_without_spec_state() -> None:
    strategy = compile_loop_strategy(
        "loop_refund",
        {
            "roles": [{"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"}],
            "steps": [
                {
                    "id": "judge",
                    "role_id": "gatekeeper",
                    "objective": "Judge closure.",
                    "action_policy": {"can_finish_run": True},
                }
            ],
            "required_target_ids": ["done_when.permission"],
        },
        max_iterations=STRATEGY_MAX_ITERATIONS,
        max_step_retries=STRATEGY_MAX_STEP_RETRIES,
        residual_risk_policy=ResidualRiskPolicy.DISALLOW,
    )

    assert strategy.roles[0].id == "gatekeeper"
    assert strategy.steps[0].id == "judge"
    assert strategy.evidence_flow.required_target_ids == ("done_when.permission",)
    assert strategy.evidence_flow.gatekeeper_step_id == "judge"
    assert strategy.iteration_policy.max_iterations == STRATEGY_MAX_ITERATIONS
    assert strategy.iteration_policy.max_step_retries == STRATEGY_MAX_STEP_RETRIES
    assert strategy.finish_policy.allow_residual_risk is False
