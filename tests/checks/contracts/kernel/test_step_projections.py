from __future__ import annotations

from loopora.engine import RunnerStepInstructionRequest, runner_step_instruction
from loopora.events.envelope import EventEnvelope
from loopora.events.step_instruction_payloads import step_instruction_event_payload
from loopora.kernel import ActorRef
from loopora.projections import (
    agent_step_view_projection,
    cli_summary_projection,
    headless_prompt_projection,
    replay_step_surfaces_projection,
    web_current_step_projection,
)


def _instruction():
    return runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id="run_projection",
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Produce proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )


def test_step_instruction_projects_to_agent_cli_web_and_headless_surfaces() -> None:
    instruction = _instruction()

    agent_view = agent_step_view_projection(instruction)
    cli_summary = cli_summary_projection(instruction)
    web_step = web_current_step_projection(instruction)
    headless_prompt = headless_prompt_projection(instruction)

    assert agent_view["kind"] == "agent_step_view"
    assert agent_view["evidence_scope"]["target_ids"] == ["done_when.proof"]
    assert cli_summary == {
        "kind": "cli_summary",
        "run_id": "run_projection",
        "step_id": "builder",
        "iteration": 1,
        "role_name": "Builder",
        "role_archetype": "builder",
        "target_count": 1,
        "can_finish_run": False,
    }
    assert web_step["identity"] == {"run_id": "run_projection", "step_id": "builder", "iteration": 1}
    assert "Produce proof." in headless_prompt
    assert "done_when.proof" in headless_prompt


def test_step_surfaces_projection_replays_latest_step_instruction_event() -> None:
    instruction = _instruction()
    event = _step_instruction_event(instruction)

    projection = replay_step_surfaces_projection([event])

    assert projection["available"] is True
    assert projection["source_sequence"] == 2
    assert projection["agent_step_view"]["step_id"] == "builder"
    assert projection["cli_summary"]["target_count"] == 1
    assert projection["cli_step_summary"]["kind"] == "cli_step_summary"
    assert projection["web_current_step"]["identity"]["run_id"] == "run_projection"
    assert "Produce proof." in projection["headless_prompt"]


def test_step_surfaces_projection_is_unavailable_after_step_commit() -> None:
    instruction = _instruction()
    committed = EventEnvelope(
        event_id="event_step_committed",
        stream_id="run:run_projection",
        aggregate_type="run",
        aggregate_id="run_projection",
        sequence=3,
        event_type="StepCommitted",
        schema_version=1,
        occurred_at="2026-01-01T00:01:00+00:00",
        actor=ActorRef(kind="runner", id="headless"),
        correlation_id="event_step_committed",
        causation_id="event_step",
        payload={
            "run_id": instruction.run_id,
            "step_id": instruction.step_id,
            "iteration": instruction.iteration,
            "result_status": "completed",
        },
    )

    projection = replay_step_surfaces_projection([_step_instruction_event(instruction), committed])

    assert projection["available"] is False
    assert projection["source_sequence"] == 3
    assert projection["agent_step_view"] == {}
    assert projection["cli_summary"] == {}
    assert projection["cli_step_summary"] == {}
    assert projection["web_current_step"] == {}
    assert projection["headless_prompt"] == ""


def _step_instruction_event(instruction) -> EventEnvelope:
    return EventEnvelope(
        event_id="event_step",
        stream_id="run:run_projection",
        aggregate_type="run",
        aggregate_id="run_projection",
        sequence=2,
        event_type="StepInstructionIssued",
        schema_version=1,
        occurred_at="2026-01-01T00:00:00+00:00",
        actor=ActorRef(kind="runner", id="headless"),
        correlation_id="event_step",
        causation_id=None,
        payload=step_instruction_event_payload(instruction),
    )
