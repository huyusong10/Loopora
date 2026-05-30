from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_event, latest_sequence, safe_int


def replay_loop_definition_projection(events: list[EventEnvelope]) -> dict:
    contract_event = latest_event(events, "LoopContractCompiled")
    strategy_event = latest_event(events, "LoopStrategyCompiled")
    activated_event = latest_event(events, "LoopActivated")
    archived_event = latest_event(events, "LoopArchived")
    contract = contract_event.payload if contract_event is not None else {}
    strategy = strategy_event.payload if strategy_event is not None else {}
    lifecycle_event = archived_event or activated_event
    lifecycle = lifecycle_event.payload if lifecycle_event is not None else {}
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_loop_definition",
        "source_sequence": latest_sequence(events),
        "loop_id": str(contract.get("loop_id") or strategy.get("loop_id") or lifecycle.get("loop_id") or ""),
        "name": str(contract.get("name") or ""),
        "task": str(contract.get("task") or ""),
        "completion_mode": str(contract.get("completion_mode") or lifecycle.get("completion_mode") or "gatekeeper"),
        "status": _loop_status(activated_event=activated_event, archived_event=archived_event),
        "check_count": safe_int(contract.get("check_count")),
        "coverage_target_count": safe_int(contract.get("coverage_target_count")),
        "role_count": safe_int(strategy.get("role_count")),
        "step_count": safe_int(strategy.get("step_count")),
        "finish_step_ids": [str(item) for item in list(strategy.get("finish_step_ids") or []) if str(item).strip()],
    }


def _loop_status(*, activated_event: EventEnvelope | None, archived_event: EventEnvelope | None) -> str:
    if archived_event is not None and (activated_event is None or archived_event.sequence > activated_event.sequence):
        return "archived"
    if activated_event is not None:
        return "active"
    return "compiled"
