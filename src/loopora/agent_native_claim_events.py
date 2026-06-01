from __future__ import annotations

from dataclasses import dataclass

from loopora.agent_native_step_view_paths import agent_native_step_contract_path_text, agent_native_step_view_path_text


@dataclass(frozen=True)
class AgentNativeStepClaimedEventRequest:
    adapter: str
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    step_view: dict


def agent_native_step_claimed_event_payload(request: AgentNativeStepClaimedEventRequest) -> dict:
    return {
        "adapter": request.adapter,
        "iter": request.iter_id,
        "step_id": request.step["id"],
        "step_order": request.step_order,
        "role_name": request.role["name"],
        "archetype": request.role["archetype"],
        "runtime_role": request.runtime_role,
        "target_agent": str((request.step_view.get("role_dispatch") or {}).get("target_agent") or ""),
        "agent_step_view_path": agent_native_step_view_path_text(request.step_view),
        "step_contract_path": agent_native_step_contract_path_text(request.step_view),
        "result_template_path": str((request.step_view.get("submit_hint") or {}).get("result_template_path") or ""),
        "parallel_group": str(request.step.get("parallel_group") or ""),
        "control_id": str(request.step.get("control_id") or ""),
    }
