from __future__ import annotations

from dataclasses import fields

from loopora.engine.run_requests import RunEngineClaimRunnerStepRequest

from runner_agent_native_architecture_support import (
    agent_native_claim_source,
    agent_native_runtime_source,
    source,
)


def test_services_use_runner_actor_factories_for_run_engine_boundaries() -> None:
    runner_source = source("service_runner_execution.py")
    agent_source = agent_native_runtime_source()

    assert "headless_runner_actor" in runner_source
    assert "agent_runner_actor" in agent_source
    assert 'ActorRef(kind="runner"' not in runner_source
    assert 'ActorRef(kind="agent"' not in agent_source


def test_services_use_engine_advance_policy_for_runner_step_selection() -> None:
    runner_source = source("service_runner_step_execution.py")
    agent_source = agent_native_claim_source()
    runner_context_source = source("engine", "runner_context.py")
    service_sources = (runner_source, agent_source)

    assert all("runner_step_claim_plan(" in source_text for source_text in service_sources)
    assert "runner_parallel_group_claim_plan(" in runner_source
    assert "_collect_runner_parallel_group" not in runner_source
    forbidden = ("select_next_runner_step", "select_next_workflow_step", "RunnerStepSelectionRequest")
    assert all(marker not in source_text for source_text in service_sources for marker in forbidden)
    assert "def runner_step_claim_plan" in runner_context_source
    assert "select_next_runner_step" in runner_context_source
    assert "def runner_parallel_group_claim_plan" in runner_context_source


def test_services_ask_run_engine_to_freeze_runner_step_instructions() -> None:
    runner_source = source("service_runner_step_execution.py")
    agent_source = agent_native_claim_source()
    runner_context_source = source("engine", "runner_context.py")
    service_sources = (runner_source, agent_source)

    assert all("runner_step_claim_request(" in source_text for source_text in service_sources)
    forbidden = (
        "RunEngineClaimRunnerStepRequest",
        "RunnerStepInstructionRequest",
        "runner_step_instruction(",
        ".claim_workflow_step(",
    )
    assert all(item not in source_text for source_text in service_sources for item in forbidden)
    assert "def runner_step_claim_request" in runner_context_source
    assert "RunEngineClaimRunnerStepRequest(" in runner_context_source
    field_names = [field.name for field in fields(RunEngineClaimRunnerStepRequest)]
    assert field_names == ["instruction", "pending_actor", "correlation_id", "causation_id"]


def test_agent_native_writes_active_step_cache_after_run_engine_claim() -> None:
    agent_source = agent_native_claim_source()
    claim_runtime_step = agent_source[
        agent_source.index("def _agent_native_claim_runtime_step")
        : agent_source.index("def _agent_native_step_view")
    ]

    assert claim_runtime_step.index(".claim_runner_step(") < claim_runtime_step.index(
        'state["active_step"] = agent_native_claimed_active_step_payload('
    )


def test_agent_native_uses_run_engine_runner_cursor_before_state_step_index() -> None:
    agent_source = agent_native_claim_source()
    agent_state_source = source("agent_native_state.py")
    agent_submit_flow_source = source("agent_native_submit_flow.py")
    runner_context_source = source("engine", "runner_context.py")

    assert ".runner_step_index(" not in agent_source
    assert ".runner_step_index(" in runner_context_source
    assert ".workflow_step_index(" not in agent_source
    assert "strategy_steps=context.strategy_steps" in runner_context_source
    assert "strategy_steps=request.context.strategy_steps" in agent_submit_flow_source
    assert all(
        marker not in agent_source
        for marker in ("workflow_steps=context.strategy_steps", "workflow_steps=request.context.strategy_steps")
    )
    assert "strategy_steps: list[dict[str, Any]]" in agent_state_source
    assert "workflow_steps: list[dict[str, Any]]" not in agent_state_source
    assert "fallback_step_index=coerced_non_negative_int(state.get(\"step_index\"))" in agent_source
    assert "fallback_step_index=int(state.get(\"step_index\") or 0)" not in agent_source
