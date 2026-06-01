from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from loopora.structured_numbers import coerced_int, coerced_non_negative_int


@dataclass(frozen=True, slots=True)
class RunnerStepSelectionRequest:
    strategy_steps: Sequence[Mapping[str, object]]
    step_index: int


@dataclass(frozen=True, slots=True)
class RunnerStepSelection:
    step_order: int
    step: Mapping[str, object]
    parallel_group: str = ""


@dataclass(frozen=True, slots=True)
class RunnerStepCursorFromEventsRequest:
    strategy_steps: Sequence[Mapping[str, object]]
    events: Sequence[object]
    iteration: int
    fallback_step_index: int = 0
    current_step_projection: Mapping[str, object] | None = None


def select_next_runner_step(request: RunnerStepSelectionRequest) -> RunnerStepSelection | None:
    step_order = coerced_non_negative_int(request.step_index)
    if step_order >= len(request.strategy_steps):
        return None
    step = request.strategy_steps[step_order]
    return RunnerStepSelection(
        step_order=step_order,
        step=step,
        parallel_group=str(step.get("parallel_group") or "").strip(),
    )


def runner_step_index_from_events(request: RunnerStepCursorFromEventsRequest) -> int:
    projected_index = _projected_current_step_index(request)
    if projected_index is not None:
        return projected_index

    last_committed_index = -1
    step_index_by_id = _step_index_by_id(request.strategy_steps)
    for event in request.events:
        if _event_type(event) != "StepCommitted":
            continue
        payload = _event_payload(event)
        if coerced_int(payload.get("iteration"), default=-1) != request.iteration:
            continue
        step_index = step_index_by_id.get(str(payload.get("step_id") or ""))
        if step_index is not None:
            last_committed_index = max(last_committed_index, step_index)
    if last_committed_index >= 0:
        return last_committed_index + 1
    return coerced_non_negative_int(request.fallback_step_index)


def _projected_current_step_index(request: RunnerStepCursorFromEventsRequest) -> int | None:
    projection = request.current_step_projection or {}
    if not projection.get("claimable"):
        return None
    if coerced_int(projection.get("iteration"), default=-1) != request.iteration:
        return None
    step_id = str(projection.get("step_id") or "")
    return _step_index_by_id(request.strategy_steps).get(step_id)


def _step_index_by_id(strategy_steps: Sequence[Mapping[str, object]]) -> dict[str, int]:
    return {
        str(step.get("id") or ""): index
        for index, step in enumerate(strategy_steps)
        if str(step.get("id") or "").strip()
    }


def _event_type(event: object) -> str:
    return str(getattr(event, "event_type", ""))


def _event_payload(event: object) -> Mapping[str, object]:
    payload = getattr(event, "payload", {})
    return payload if isinstance(payload, Mapping) else {}
