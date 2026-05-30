from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.events.replay import replay_run_snapshot
from loopora.events.step_instruction_payloads import step_instruction_from_event_payload
from loopora.kernel import StepInstruction
from loopora.projections._event_replay_support import (
    EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
    latest_event,
    latest_sequence,
    safe_int,
)
from loopora.projections.agent_step_view import agent_step_view_projection
from loopora.projections.cli_summary import cli_summary_projection
from loopora.projections.headless_prompt import headless_prompt_projection
from loopora.projections.web_current_step import web_current_step_projection


def replay_step_surfaces_projection(events: list[EventEnvelope]) -> dict:
    source_sequence = latest_sequence(events)
    event = latest_event(events, "StepInstructionIssued")
    if event is None:
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_step_surfaces",
            "source_sequence": source_sequence,
            "available": False,
            "agent_step_view": {},
            "cli_summary": {},
            "cli_step_summary": {},
            "web_current_step": {},
            "headless_prompt": "",
        }
    snapshot = replay_run_snapshot(events)
    if (
        snapshot.state.current_step_id != str(event.payload.get("step_id") or "")
        or snapshot.state.current_iteration != safe_int(event.payload.get("iteration"))
        or snapshot.state.pending_actor is None
    ):
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_step_surfaces",
            "source_sequence": source_sequence,
            "available": False,
            "agent_step_view": {},
            "cli_summary": {},
            "cli_step_summary": {},
            "web_current_step": {},
            "headless_prompt": "",
        }
    instruction = _step_instruction_from_event(event)
    cli_summary = cli_summary_projection(instruction)
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_step_surfaces",
        "source_sequence": source_sequence,
        "available": True,
        "agent_step_view": agent_step_view_projection(instruction),
        "cli_summary": cli_summary,
        "cli_step_summary": {**cli_summary, "kind": "cli_step_summary"},
        "web_current_step": web_current_step_projection(instruction),
        "headless_prompt": headless_prompt_projection(instruction),
    }


replay_step_surface_projection_bundle = replay_step_surfaces_projection


def _step_instruction_from_event(event: EventEnvelope) -> StepInstruction:
    return step_instruction_from_event_payload(event.payload, fallback_run_id=event.aggregate_id)
