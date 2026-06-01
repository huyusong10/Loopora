from __future__ import annotations

from loopora.events.run_event_payloads import (
    step_claimed_payload,
    step_committed_payload,
    step_instruction_payload,
    step_planned_payload,
    step_submitted_payload,
)
from loopora.engine.run_requests import (
    RunEngineClaimStepRequest,
    RunEngineClaimRunnerStepRequest,
    RunEngineClaimRunnerStepResult,
    RunEngineSubmitStepRequest,
    RunEngineSubmitStepResult,
)
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.engine.step_submission_guard import require_step_submission_guard
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_step_event_transactions import (
    append_step_claim_events_and_rebuild_projection_cache,
    append_step_submission_events_and_rebuild_projection_cache,
)


def append_step_instruction_and_rebuild_projection_cache(
    repository,
    request: RunEngineClaimStepRequest,
) -> EventEnvelope:
    instruction = request.instruction
    result = append_step_claim_events_and_rebuild_projection_cache(
        repository,
        run_id=instruction.run_id,
        planned_request=RunEventAppend(
            run_id=instruction.run_id,
            event_type="StepPlanned",
            actor=request.pending_actor,
            payload=step_planned_payload(instruction),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
        claimed_request=RunEventAppend(
            run_id=instruction.run_id,
            event_type="StepClaimed",
            actor=request.pending_actor,
            payload=step_claimed_payload(
                instruction,
                pending_actor=request.pending_actor.to_dict(),
            ),
            correlation_id=request.correlation_id,
            causation_id=None,
        ),
        instruction_request=RunEventAppend(
            run_id=instruction.run_id,
            event_type="StepInstructionIssued",
            actor=request.pending_actor,
            payload={
                **step_instruction_payload(instruction),
                "pending_actor": request.pending_actor.to_dict(),
            },
            correlation_id=request.correlation_id,
            causation_id=None,
        ),
    )
    return result.instruction_event


def append_runner_step_instruction_and_rebuild_projection_cache(
    repository,
    request: RunEngineClaimRunnerStepRequest,
) -> RunEngineClaimRunnerStepResult:
    instruction = request.instruction
    event = append_step_instruction_and_rebuild_projection_cache(
        repository,
        RunEngineClaimStepRequest(
            instruction=instruction,
            pending_actor=request.pending_actor,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )
    return RunEngineClaimRunnerStepResult(instruction=instruction, event=event)


def append_step_submission_and_rebuild_projection_cache(
    repository,
    request: RunEngineSubmitStepRequest,
) -> RunEngineSubmitStepResult:
    result = request.result
    require_step_submission_guard(repository, result)
    loop_id = run_snapshot_from_repository(repository, result.run_id).state.loop_id
    return append_step_submission_events_and_rebuild_projection_cache(
        repository,
        result,
        loop_id=loop_id,
        submitted_request=RunEventAppend(
            run_id=result.run_id,
            event_type="StepSubmitted",
            actor=result.actor,
            payload=step_submitted_payload(result),
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
        committed_request=RunEventAppend(
            run_id=result.run_id,
            event_type="StepCommitted",
            actor=result.actor,
            payload=step_committed_payload(
                run_id=result.run_id,
                step_id=result.step_id,
                iteration=result.iteration,
                result_status=result.status.value,
            ),
            correlation_id=request.correlation_id,
            causation_id=None,
        ),
    )


def validate_step_submission_against_event_stream(
    repository,
    request: RunEngineSubmitStepRequest,
) -> None:
    require_step_submission_guard(repository, request.result)
