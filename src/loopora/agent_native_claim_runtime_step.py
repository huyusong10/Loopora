from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loopora.agent_native_parallel_groups import agent_native_claim_input_snapshot
from loopora.agent_native_evidence_contracts import agent_native_active_step_view_fields
from loopora.runner_step_runtime_requests import (
    RunnerStepRuntimeInputSnapshot,
    RunnerStepRuntimeRequestBuildRequest,
    build_runner_step_runtime_request,
)
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY, step_instruction_context_from_mapping
from loopora.utils import utc_now


@dataclass(frozen=True, slots=True)
class AgentNativeRuntimeStepViewBuildRequest:
    kind: str
    run: dict[str, Any]
    state: dict[str, Any]
    context: Any
    iteration: Any
    step: dict[str, Any]
    step_order: int
    role: dict[str, Any]
    execution_settings: dict[str, Any]
    entry_source: str
    runtime_role_key: Callable[[dict[str, Any]], str]
    prepare_runner_step_request: Callable[[Any], dict[str, Any]]
    step_view_builder: Callable[..., dict[str, Any]]


@dataclass(frozen=True, slots=True)
class AgentNativeRuntimeStepViewBuildResult:
    runtime_role: str
    role_request: Any
    step_instruction_context: dict[str, Any]
    step_view: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AgentNativeClaimedActiveStepPayloadRequest:
    step_view: dict[str, Any]
    step_instruction_context: dict[str, Any]
    execution_settings: dict[str, Any]
    role: dict[str, Any]
    runtime_role: str
    step: dict[str, Any]
    step_order: int
    iter_id: int


def build_agent_native_runtime_step_view(
    request: AgentNativeRuntimeStepViewBuildRequest,
) -> AgentNativeRuntimeStepViewBuildResult:
    claim_snapshot = agent_native_claim_input_snapshot(
        request.state,
        request.context,
        request.iteration,
        request.step,
        request.step_order,
        runtime_role_key=request.runtime_role_key,
    )
    prepared = request.prepare_runner_step_request(
        build_runner_step_runtime_request(
            RunnerStepRuntimeRequestBuildRequest(
                context=request.context,
                iteration=request.iteration,
                run=request.run,
                step=request.step,
                step_order=request.step_order,
                role=request.role,
                execution_settings=request.execution_settings,
                input_snapshot=RunnerStepRuntimeInputSnapshot(
                    current_outputs_by_step=claim_snapshot.current_outputs_by_step,
                    current_outputs_by_role=claim_snapshot.current_outputs_by_role,
                    current_outputs_by_archetype=claim_snapshot.current_outputs_by_archetype,
                    current_handoffs=claim_snapshot.current_handoffs,
                    evidence_items_snapshot=claim_snapshot.evidence_items_snapshot,
                ),
            ),
        )
    )
    runtime_role = str(prepared["runtime_role"])
    role_request = prepared["role_request"]
    step_instruction_context = step_instruction_context_from_mapping(prepared)
    evidence_context = (
        step_instruction_context.get("evidence") if isinstance(step_instruction_context.get("evidence"), dict) else {}
    )
    step_view = request.step_view_builder(
        request.kind,
        run=request.run,
        layout=request.context.layout,
        iter_id=request.iteration.iter_id,
        step=request.step,
        step_order=request.step_order,
        role=request.role,
        runtime_role=runtime_role,
        prompt=str(prepared["prompt"]),
        output_schema=role_request.output_schema,
        known_evidence_ids=list(
            dict.fromkeys(str(item) for item in list(evidence_context.get("known_ids") or []) if str(item).strip())
        ),
        step_instruction_context=step_instruction_context,
        entry_source=request.entry_source,
    )
    return AgentNativeRuntimeStepViewBuildResult(
        runtime_role=runtime_role,
        role_request=role_request,
        step_instruction_context=step_instruction_context,
        step_view=step_view,
    )


def agent_native_claimed_active_step_payload(
    request: AgentNativeClaimedActiveStepPayloadRequest,
) -> dict[str, Any]:
    return {
        "claimed_at": utc_now(),
        **agent_native_active_step_view_fields(request.step_view),
        STEP_INSTRUCTION_CONTEXT_KEY: request.step_instruction_context,
        "execution_settings": request.execution_settings,
        "role": request.role,
        "runtime_role": request.runtime_role,
        "step": request.step,
        "step_order": request.step_order,
        "iter_id": request.iter_id,
    }
