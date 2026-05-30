from __future__ import annotations

from loopora.engine.run_evidence_commands import (
    append_coverage_recompute_and_rebuild_projection_cache,
    append_evidence_acceptance_and_rebuild_projection_cache,
    append_step_evidence_and_rebuild_projection_cache,
)
from loopora.engine.run_iteration_commands import (
    append_iteration_completion_if_absent_and_rebuild_projection_cache,
    append_iteration_start_if_absent_and_rebuild_projection_cache,
)
from loopora.engine.run_lifecycle import RunEngineAdvanceOutcome
from loopora.engine.run_lifecycle_commands import advance_run, start_run
from loopora.engine.run_requests import (
    RunEngineAcceptEvidenceRequest,
    RunEngineClaimStepRequest,
    RunEngineClaimRunnerStepRequest,
    RunEngineClaimRunnerStepResult,
    RunEngineCommitStepRequest,
    RunEngineCompleteIterationRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueStepRequest,
    RunEngineIssueVerdictRequest,
    RunEngineRecordStepEvidenceRequest,
    RunEngineRecordStepEvidenceResult,
    RunEngineStartIterationRequest,
    RunEngineSubmitStepRequest,
    RunEngineSubmitStepResult,
)
from loopora.engine.run_snapshot_source import run_snapshot_from_repository
from loopora.engine.run_step_commands import (
    append_step_commit_and_rebuild_projection_cache,
    append_step_instruction_and_rebuild_projection_cache,
    append_step_submission_and_rebuild_projection_cache,
    append_runner_step_instruction_and_rebuild_projection_cache,
)
from loopora.engine.run_verdict_commands import append_verdict_issue_and_rebuild_projection_cache
from loopora.engine.run_step_cursor import runner_step_index_for_run
from loopora.events.replay import RunSnapshot


class RepositoryRunEngine:
    """Thin transition adapter: event replay first, legacy run table fallback."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def start(self, run_id: str) -> RunEngineAdvanceOutcome:
        return start_run(self.repository, run_id)

    def claim_step(self, request: RunEngineClaimStepRequest):
        return append_step_instruction_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def claim_runner_step(self, request: RunEngineClaimRunnerStepRequest) -> RunEngineClaimRunnerStepResult:
        return append_runner_step_instruction_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def runner_step_index(
        self,
        run_id: str,
        *,
        strategy_steps: list[dict],
        iteration: int,
        fallback_step_index: int = 0,
    ) -> int:
        return runner_step_index_for_run(
            self.repository,
            run_id,
            strategy_steps=strategy_steps,
            iteration=iteration,
            fallback_step_index=fallback_step_index,
        )

    def issue_step_instruction(self, request: RunEngineIssueStepRequest):
        return self.claim_step(request)

    def submit_step(self, request: RunEngineSubmitStepRequest) -> RunEngineSubmitStepResult:
        return append_step_submission_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def commit_step(self, request: RunEngineCommitStepRequest):
        return append_step_commit_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def accept_evidence(self, request: RunEngineAcceptEvidenceRequest):
        return append_evidence_acceptance_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def recompute_coverage(self, request: RunEngineCoverageRecomputedRequest):
        return append_coverage_recompute_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def record_step_evidence(self, request: RunEngineRecordStepEvidenceRequest) -> RunEngineRecordStepEvidenceResult:
        return append_step_evidence_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def issue_verdict(self, request: RunEngineIssueVerdictRequest):
        return append_verdict_issue_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def start_iteration(self, request: RunEngineStartIterationRequest):
        return append_iteration_start_if_absent_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def complete_iteration(self, request: RunEngineCompleteIterationRequest):
        return append_iteration_completion_if_absent_and_rebuild_projection_cache(
            self.repository,
            request,
        )

    def advance(self, run_id: str) -> RunEngineAdvanceOutcome:
        return advance_run(self.repository, run_id)

    def snapshot(self, run_id: str) -> RunSnapshot:
        return run_snapshot_from_repository(self.repository, run_id)
