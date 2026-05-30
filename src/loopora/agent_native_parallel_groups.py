from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loopora.run_artifacts import read_jsonl


@dataclass(frozen=True)
class AgentNativeClaimInputSnapshot:
    current_outputs_by_step: dict[str, dict]
    current_outputs_by_role: dict[str, dict]
    current_outputs_by_archetype: dict[str, dict]
    current_handoffs: list[dict]
    evidence_items_snapshot: list[dict] | None = None


def agent_native_claim_input_snapshot(  # noqa: PLR0913 - this projects an explicit runtime step boundary.
    state: dict[str, Any],
    context: Any,
    iteration: Any,
    step: dict,
    step_order: int,
    *,
    runtime_role_key: Callable[[dict], str],
) -> AgentNativeClaimInputSnapshot:
    parallel_group = str(step.get("parallel_group") or "").strip()
    if not parallel_group:
        state["parallel_group_snapshot"] = {}
        return AgentNativeClaimInputSnapshot(
            current_outputs_by_step=dict(iteration.current_outputs_by_step),
            current_outputs_by_role=dict(iteration.current_outputs_by_role),
            current_outputs_by_archetype=dict(iteration.current_outputs_by_archetype),
            current_handoffs=list(iteration.current_handoffs),
        )

    snapshot = agent_native_parallel_group_snapshot(
        state,
        context,
        iteration,
        step_order,
        parallel_group,
        runtime_role_key=runtime_role_key,
    )
    return AgentNativeClaimInputSnapshot(
        current_outputs_by_step=dict(snapshot.get("current_outputs_by_step") or {}),
        current_outputs_by_role=dict(snapshot.get("current_outputs_by_role") or {}),
        current_outputs_by_archetype=dict(snapshot.get("current_outputs_by_archetype") or {}),
        current_handoffs=list(snapshot.get("current_handoffs") or []),
        evidence_items_snapshot=[item for item in list(snapshot.get("evidence_items") or []) if isinstance(item, dict)],
    )


def agent_native_parallel_group_snapshot(  # noqa: PLR0913 - snapshot inputs mirror the runtime boundary.
    state: dict[str, Any],
    context: Any,
    iteration: Any,
    step_order: int,
    parallel_group: str,
    *,
    runtime_role_key: Callable[[dict], str],
) -> dict[str, Any]:
    group_start, group_end, group_step_ids = agent_native_parallel_group_bounds(
        context.strategy_steps,
        step_order,
        parallel_group,
    )
    existing = state.get("parallel_group_snapshot") if isinstance(state.get("parallel_group_snapshot"), dict) else {}
    if (
        existing
        and _agent_native_int(existing.get("iter_id"), default=-1) == iteration.iter_id
        and str(existing.get("parallel_group") or "") == parallel_group
        and _agent_native_int(existing.get("group_start"), default=-1) == group_start
        and _agent_native_int(existing.get("group_end"), default=-1) == group_end
    ):
        return existing

    group_step_id_set = set(group_step_ids)
    group_roles = [context.role_by_id[step["role_id"]] for step in context.strategy_steps[group_start:group_end]]
    group_role_ids = {str(role["id"]) for role in group_roles}
    group_runtime_roles = {runtime_role_key(role) for role in group_roles}
    group_archetypes = {str(role["archetype"]) for role in group_roles}
    snapshot = {
        "iter_id": iteration.iter_id,
        "parallel_group": parallel_group,
        "group_start": group_start,
        "group_end": group_end,
        "step_ids": group_step_ids,
        "current_outputs_by_step": {
            step_id: output for step_id, output in iteration.current_outputs_by_step.items() if step_id not in group_step_id_set
        },
        "current_outputs_by_role": {
            role_id: output
            for role_id, output in iteration.current_outputs_by_role.items()
            if role_id not in group_role_ids and role_id not in group_runtime_roles
        },
        "current_outputs_by_archetype": {
            archetype: output for archetype, output in iteration.current_outputs_by_archetype.items() if archetype not in group_archetypes
        },
        "current_handoffs": [
            handoff
            for handoff in iteration.current_handoffs
            if _handoff_step_id(handoff) not in group_step_id_set
        ],
        "evidence_items": [
            item
            for item in read_jsonl(context.layout.evidence_ledger_path)
            if not (
                isinstance(item, dict)
                and _agent_native_int(item.get("iter"), default=-1) == iteration.iter_id
                and str(item.get("step_id") or "") in group_step_id_set
            )
        ],
    }
    state["parallel_group_snapshot"] = snapshot
    return snapshot


def agent_native_parallel_group_started_payload(
    steps: list[dict],
    iter_id: int,
    step: dict,
    step_order: int,
) -> dict[str, object] | None:
    parallel_group = str(step.get("parallel_group") or "").strip()
    if not parallel_group:
        return None
    group_start, _group_end, _group_step_ids = agent_native_parallel_group_bounds(steps, step_order, parallel_group)
    if step_order != group_start:
        return None
    return agent_native_parallel_group_event_payload(steps, iter_id, step_order, parallel_group)


def agent_native_parallel_group_finished_payload(
    steps: list[dict],
    iter_id: int,
    step: dict,
    step_order: int,
) -> dict[str, object] | None:
    parallel_group = str(step.get("parallel_group") or "").strip()
    if not parallel_group:
        return None
    next_step_order = step_order + 1
    if next_step_order < len(steps) and str(steps[next_step_order].get("parallel_group") or "").strip() == parallel_group:
        return None
    return agent_native_parallel_group_event_payload(steps, iter_id, step_order, parallel_group)


def agent_native_parallel_group_event_payload(
    steps: list[dict],
    iter_id: int,
    step_order: int,
    parallel_group: str,
) -> dict[str, object]:
    group_start, _group_end, group_step_ids = agent_native_parallel_group_bounds(steps, step_order, parallel_group)
    return {
        "iter": iter_id,
        "parallel_group": parallel_group,
        "step_orders": list(range(group_start, group_start + len(group_step_ids))),
        "step_ids": group_step_ids,
    }


def agent_native_parallel_group_bounds(steps: list[dict], step_order: int, parallel_group: str) -> tuple[int, int, list[str]]:
    group_start = step_order
    while group_start > 0 and str(steps[group_start - 1].get("parallel_group") or "").strip() == parallel_group:
        group_start -= 1
    group_end = step_order + 1
    while group_end < len(steps) and str(steps[group_end].get("parallel_group") or "").strip() == parallel_group:
        group_end += 1
    return group_start, group_end, [str(step["id"]) for step in steps[group_start:group_end]]


def _agent_native_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _handoff_step_id(handoff: object) -> str:
    if not isinstance(handoff, dict):
        return ""
    source = handoff.get("source") if isinstance(handoff.get("source"), dict) else {}
    return str(source.get("step_id") or "")
