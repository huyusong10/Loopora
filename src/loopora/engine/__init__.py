from __future__ import annotations

from loopora.engine.advance_policy import (
    RunnerStepCursorFromEventsRequest,
    RunnerStepSelection,
    RunnerStepSelectionRequest,
    select_next_runner_step,
    runner_step_index_from_events,
)
from loopora.engine.evidence_engine import EvidenceEngine
from loopora.engine.evidence_engine_adapter import (
    RunnerStepEvidenceArtifactsRequest,
    RunnerStepEvidenceArtifactsResult,
    write_runner_step_evidence_artifacts,
)
from loopora.engine.run_engine import RepositoryRunEngine
from loopora.engine.run_lifecycle import RunEngineAdvanceOutcome, RunEngineAdvanceStatus
from loopora.engine.run_requests import (
    RunEngineAcceptEvidenceRequest,
    RunEngineClaimStepRequest,
    RunEngineClaimRunnerStepRequest,
    RunEngineClaimRunnerStepResult,
    RunEngineCompleteIterationRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineFailRunRequest,
    RunEngineIssueStepRequest,
    RunEngineIssueVerdictRequest,
    RunEngineIssueVerdictResult,
    RunEngineRecordStepEvidenceRequest,
    RunEngineRecordStepEvidenceResult,
    RunEngineStartIterationRequest,
    RunEngineStopRunRequest,
    RunEngineSubmitStepRequest,
    RunEngineSubmitStepResult,
)
from loopora.engine.step_instruction import RunnerStepInstructionRequest, runner_step_instruction
from loopora.engine.step_result import RunnerStepResultRequest, runner_step_result
from loopora.engine.verdict_engine_adapter import (
    coverage_state_from_legacy_projection,
    verdict_event_payload_from_kernel_verdict,
    verdict_from_legacy_coverage_projection,
)
from loopora.engine.verdict_engine import VerdictEngine

__all__ = [
    "EvidenceEngine",
    "RepositoryRunEngine",
    "RunEngineAcceptEvidenceRequest",
    "RunEngineAdvanceOutcome",
    "RunEngineAdvanceStatus",
    "RunEngineClaimRunnerStepRequest",
    "RunEngineClaimRunnerStepResult",
    "RunEngineClaimStepRequest",
    "RunEngineCompleteIterationRequest",
    "RunEngineCoverageRecomputedRequest",
    "RunEngineFailRunRequest",
    "RunEngineIssueStepRequest",
    "RunEngineIssueVerdictRequest",
    "RunEngineIssueVerdictResult",
    "RunEngineRecordStepEvidenceRequest",
    "RunEngineRecordStepEvidenceResult",
    "RunEngineStartIterationRequest",
    "RunEngineStopRunRequest",
    "RunEngineSubmitStepRequest",
    "RunEngineSubmitStepResult",
    "RunnerStepCursorFromEventsRequest",
    "RunnerStepEvidenceArtifactsRequest",
    "RunnerStepEvidenceArtifactsResult",
    "RunnerStepInstructionRequest",
    "RunnerStepResultRequest",
    "RunnerStepSelection",
    "RunnerStepSelectionRequest",
    "VerdictEngine",
    "coverage_state_from_legacy_projection",
    "runner_step_index_from_events",
    "runner_step_instruction",
    "runner_step_result",
    "select_next_runner_step",
    "verdict_event_payload_from_kernel_verdict",
    "verdict_from_legacy_coverage_projection",
    "write_runner_step_evidence_artifacts",
]
