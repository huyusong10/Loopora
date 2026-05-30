from __future__ import annotations

from typing import Any

from loopora.agent_native_context_coverage import agent_native_context_packet_with_coverage
from loopora.agent_native_step_view import AgentNativeStepViewRequest, agent_native_step_view
from loopora.agent_native_step_view_refresh import refresh_agent_native_step_view_with_judgment_contract

AgentNativeCapsuleRequest = AgentNativeStepViewRequest


def agent_native_capsule(request: AgentNativeCapsuleRequest) -> dict[str, Any]:
    return agent_native_step_view(request)


def refresh_agent_native_capsule_with_judgment_contract(
    run: dict[str, Any],
    capsule: object,
    *,
    context_packet: object = None,
) -> dict[str, Any]:
    return refresh_agent_native_step_view_with_judgment_contract(run, capsule, context_packet=context_packet)

__all__ = [
    "AgentNativeCapsuleRequest",
    "AgentNativeStepViewRequest",
    "agent_native_capsule",
    "agent_native_context_packet_with_coverage",
    "agent_native_step_view",
    "refresh_agent_native_capsule_with_judgment_contract",
    "refresh_agent_native_step_view_with_judgment_contract",
]
