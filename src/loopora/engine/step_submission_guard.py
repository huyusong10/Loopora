from __future__ import annotations

from collections.abc import Mapping, Sequence

from loopora.events.envelope import EventEnvelope
from loopora.events.projection_cache import current_step_projection_for_run
from loopora.events.run_event_queries import list_run_events
from loopora.kernel import ActorRef, StepResult
from loopora.structured_numbers import coerced_int

_ACTOR_IDENTITY_KEYS = ("kind", "id", "adapter")


def require_step_submission_guard(repository: object, result: StepResult) -> None:
    events = list_run_events(repository, result.run_id)
    _require_result_not_already_committed(events, result)
    projection = current_step_projection_for_run(repository, result.run_id)
    if projection.get("claimable"):
        _require_result_matches_claimed_step(result, projection, events)


def _require_result_matches_claimed_step(
    result: StepResult,
    projection: Mapping[str, object],
    events: Sequence[EventEnvelope],
) -> None:
    if _result_matches_projection(result, projection):
        return
    if _result_matches_open_parallel_instruction(result, events):
        return
    raise ValueError("StepResult does not match current StepInstruction")


def _result_matches_projection(result: StepResult, projection: Mapping[str, object]) -> bool:
    active_step_id = str(projection.get("step_id") or "").strip()
    active_iteration = coerced_int(projection.get("iteration"), default=-1)
    if result.step_id != active_step_id or result.iteration != active_iteration:
        return False
    return _result_actor_matches_pending_actor(result, projection.get("pending_actor"))


def _result_matches_open_parallel_instruction(result: StepResult, events: Sequence[EventEnvelope]) -> bool:
    for event in reversed(events):
        if event.event_type != "StepInstructionIssued":
            continue
        payload = event.payload
        if str(payload.get("step_id") or "").strip() != result.step_id:
            continue
        if coerced_int(payload.get("iteration"), default=-1) != result.iteration:
            continue
        action_policy = payload.get("action_policy") if isinstance(payload.get("action_policy"), Mapping) else {}
        if not action_policy.get("can_spawn_parallel"):
            continue
        return _result_actor_matches_pending_actor(result, payload.get("pending_actor"))
    return False


def _result_actor_matches_pending_actor(result: StepResult, pending_actor: object) -> bool:
    expected_actor = _actor_identity(pending_actor)
    if not expected_actor:
        return True
    actual_actor = _actor_identity(result.actor)
    return all(actual_actor.get(key) == value for key, value in expected_actor.items())


def _actor_identity(actor: ActorRef | object) -> dict[str, str]:
    payload = actor.to_dict() if isinstance(actor, ActorRef) else actor
    if not isinstance(payload, Mapping):
        return {}
    return {
        key: str(payload.get(key) or "").strip()
        for key in _ACTOR_IDENTITY_KEYS
        if str(payload.get(key) or "").strip()
    }


def _require_result_not_already_committed(events: Sequence[EventEnvelope], result: StepResult) -> None:
    for event in reversed(events):
        if event.event_type != "StepCommitted":
            continue
        payload = event.payload
        if str(payload.get("step_id") or "").strip() != result.step_id:
            continue
        if coerced_int(payload.get("iteration"), default=-1) == result.iteration:
            raise ValueError("StepResult was already committed for this step")
