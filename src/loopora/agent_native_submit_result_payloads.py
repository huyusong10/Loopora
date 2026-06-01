from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.runners import agent_runner_actor
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY


def agent_native_submitted_session_ref(request_session_ref: object, output: dict[str, Any]) -> dict:
    if isinstance(request_session_ref, dict):
        return request_session_ref
    session_ref = output.get("session_ref")
    return session_ref if isinstance(session_ref, dict) else {}


@dataclass(frozen=True)
class AgentNativeStepResultPayloadRequest:
    kind: str
    active: dict[str, Any]
    step: dict[str, Any]
    role: dict[str, Any]
    runtime_role: str
    normalized_output: dict[str, Any]
    step_instruction_context: dict[str, Any]
    iter_id: int
    step_order: int
    session_ref: dict


def agent_native_step_result_payload(request: AgentNativeStepResultPayloadRequest) -> dict[str, Any]:
    return {
        "skipped": False,
        "step_order": request.step_order,
        "step": request.step,
        "role": request.role,
        "runtime_role": request.runtime_role,
        "execution_settings": request.active.get("execution_settings")
        if isinstance(request.active.get("execution_settings"), dict)
        else {},
        "normalized_output": request.normalized_output,
        STEP_INSTRUCTION_CONTEXT_KEY: request.step_instruction_context,
        "session_ref": request.session_ref,
        "actor_ref": agent_runner_actor(request.kind).to_dict(),
        "duration_ms": 0,
        "iter_id": request.iter_id,
    }
