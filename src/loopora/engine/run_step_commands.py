from __future__ import annotations

from loopora.events.run_event_payloads import (
    step_committed_payload,
    step_instruction_payload,
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
from loopora.engine.step_instruction import RunnerStepInstructionRequest, runner_step_instruction
from loopora.events.append_requests import RunEventAppend
from loopora.events.envelope import EventEnvelope
from loopora.events.run_event_commands import append_run_event_and_rebuild_projection_cache
from loopora.events.run_event_transactions import append_step_submission_events_and_rebuild_projection_cache


def append_step_instruction_and_rebuild_projection_cache(
    repository,
    request: RunEngineClaimStepRequest,
) -> EventEnvelope:
    instruction = request.instruction
    return append_run_event_and_rebuild_projection_cache(
        repository,
        RunEventAppend(
            run_id=instruction.run_id,
            event_type="StepInstructionIssued",
            actor=request.pending_actor,
            payload={
                **step_instruction_payload(instruction),
                "pending_actor": request.pending_actor.to_dict(),
            },
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
        ),
    )

def append_runner_step_instruction_and_rebuild_projection_cache(
    repository,
    request: RunEngineClaimRunnerStepRequest,
) -> RunEngineClaimRunnerStepResult:
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id=request.run_id,
            contract_ref=request.contract_ref,
            compiled_spec=request.compiled_spec,
            iteration=request.iteration,
            step=request.step,
            role=request.role,
        )
    )
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
