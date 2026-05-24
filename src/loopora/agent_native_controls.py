from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from loopora.service_workflow_controls import (
    WorkflowControlPayloadRequest,
    WorkflowControlStepRequest,
    build_workflow_control_payload,
    build_workflow_control_step,
    matching_workflow_controls,
    workflow_control_after_seconds,
    workflow_iteration_control_triggers,
)
from loopora.structured_numbers import structured_non_negative_int


@dataclass(frozen=True)
class AgentNativeControlQueueRequest:
    run: dict[str, Any]
    state: dict[str, Any]
    context: Any
    iteration: Any
    append_run_event: Callable[..., None]


@dataclass(frozen=True)
class _AgentNativeControlSignalRequest:
    run: dict[str, Any]
    context: Any
    iteration: Any
    queue: list[dict[str, Any]]
    signal: str
    trigger: dict[str, object]
    append_run_event: Callable[..., None]


def agent_native_control_queue_iter_matches(value: object, iter_id: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == iter_id


def agent_native_control_queue_index(state: dict[str, Any], *, queue: list[dict[str, Any]]) -> int:
    if "control_queue_index" not in state or state.get("control_queue_index") is None:
        return 0
    value = state.get("control_queue_index")
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return len(queue)


def agent_native_control_queue_step_order(entry: dict[str, Any]) -> int | None:
    value = entry.get("step_order")
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def agent_native_build_control_queue(request: AgentNativeControlQueueRequest) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for trigger in workflow_iteration_control_triggers(request.iteration.current_gatekeeper_result, request.iteration.stagnation):
        _agent_native_append_controls_for_signal(
            _AgentNativeControlSignalRequest(
                run=request.run,
                context=request.context,
                iteration=request.iteration,
                queue=queue,
                signal=trigger.signal,
                trigger=trigger.trigger,
                append_run_event=request.append_run_event,
            )
        )
    request.state["control_fire_counts"] = dict(request.context.control_fire_counts)
    return queue


def _agent_native_append_controls_for_signal(request: _AgentNativeControlSignalRequest) -> None:
    matching_controls = matching_workflow_controls(request.context.workflow_controls, request.signal)
    if not matching_controls:
        return
    for control in matching_controls:
        control_id = str(control.get("id") or "").strip()
        max_fires = structured_non_negative_int(control.get("max_fires_per_run"), default=1) or 1
        fired = _agent_native_control_fire_count(request.context.control_fire_counts.get(control_id), max_fires=max_fires)
        role_id = str((control.get("call") or {}).get("role_id") or "").strip()
        elapsed_seconds = _agent_native_elapsed_seconds(request.run)
        base_payload = build_workflow_control_payload(
            WorkflowControlPayloadRequest(
                control=control,
                iter_id=request.iteration.iter_id,
                signal=request.signal,
                trigger=request.trigger,
                elapsed_seconds=elapsed_seconds,
            )
        )
        if fired >= max_fires:
            request.append_run_event(
                request.context.run_id,
                "control_skipped",
                {**base_payload, "skip_reason": "max_fires_per_run"},
            )
            continue
        if elapsed_seconds < workflow_control_after_seconds(base_payload["after"]):
            request.append_run_event(
                request.context.run_id,
                "control_skipped",
                {**base_payload, "skip_reason": "after_not_elapsed"},
            )
            continue
        role = request.context.role_by_id.get(role_id)
        if not role:
            request.append_run_event(
                request.context.run_id,
                "control_failed",
                {**base_payload, "error": "control role not found"},
            )
            continue
        request.context.control_fire_counts[control_id] = fired + 1
        existing_control_count = sum(1 for item in request.iteration.step_results if item["step"].get("control_id")) + len(request.queue)
        control_step, control_order = build_workflow_control_step(
            WorkflowControlStepRequest(
                control=control,
                payload=base_payload,
                role=role,
                workflow_step_count=len(request.context.workflow_steps),
                existing_control_count=existing_control_count,
            )
        )
        request.append_run_event(request.context.run_id, "control_triggered", base_payload, role=role_id)
        request.queue.append({"step": control_step, "step_order": control_order})


def _agent_native_control_fire_count(value: object, *, max_fires: int) -> int:
    if value is None:
        return 0
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return max_fires


def _agent_native_elapsed_seconds(run: dict[str, Any]) -> float:
    started_at = str(run.get("started_at") or run.get("queued_at") or run.get("created_at") or "").strip()
    if not started_at:
        return 0.0
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    return max((datetime.now(UTC) - started.astimezone(UTC)).total_seconds(), 0.0)
