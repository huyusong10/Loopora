from __future__ import annotations

from dataclasses import dataclass

from loopora.events.envelope import EventEnvelope
from loopora.kernel import StepResult
from loopora.kernel.actors import ActorRef
from loopora.kernel.step import StepInstruction


@dataclass(frozen=True, slots=True)
class RunEngineIssueStepRequest:
    instruction: StepInstruction
    pending_actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


RunEngineClaimStepRequest = RunEngineIssueStepRequest


@dataclass(frozen=True, slots=True)
class RunEngineClaimRunnerStepRequest:
    run_id: str
    contract_ref: str
    compiled_spec: dict
    iteration: int
    step: dict
    role: dict
    pending_actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineClaimRunnerStepResult:
    instruction: StepInstruction
    event: object


@dataclass(frozen=True, slots=True)
class RunEngineCommitStepRequest:
    run_id: str
    step_id: str
    iteration: int
    actor: ActorRef
    result_status: str = "completed"
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineSubmitStepRequest:
    result: StepResult
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineSubmitStepResult:
    submitted_event: EventEnvelope
    committed_event: EventEnvelope


@dataclass(frozen=True, slots=True)
class RunEngineAcceptEvidenceRequest:
    run_id: str
    evidence_entry: dict
    actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineCoverageRecomputedRequest:
    run_id: str
    coverage_projection: dict
    actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineRecordStepEvidenceRequest:
    run_id: str
    evidence_entry: dict
    coverage_projection: dict
    actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineRecordStepEvidenceResult:
    evidence_event: EventEnvelope
    coverage_event: EventEnvelope


@dataclass(frozen=True, slots=True)
class RunEngineIssueVerdictRequest:
    run_id: str
    verdict: dict
    actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineStartIterationRequest:
    run_id: str
    iteration: int
    actor: ActorRef
    step_count: int = 0
    correlation_id: str = ""
    causation_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunEngineCompleteIterationRequest:
    run_id: str
    iteration: int
    actor: ActorRef
    completed_step_count: int = 0
    reason: str = ""
    correlation_id: str = ""
    causation_id: str | None = None
