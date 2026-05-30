from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from loopora.engine.advance_policy import WorkflowCursorFromEventsRequest, workflow_step_index_from_events
from loopora.engine.step_instruction import WorkflowStepInstructionRequest, workflow_step_instruction
from loopora.events.envelope import EventEnvelope
from loopora.events.replay import RunSnapshot, replay_run_snapshot
from loopora.events.streams import run_stream_id
from loopora.events.store import DomainEventAppendRequest
from loopora.kernel import StepResult
from loopora.kernel.actors import ActorRef
from loopora.kernel.run_state import RunLifecycleStatus, RunState
from loopora.kernel.step import StepInstruction
from loopora.kernel.verdict import VerdictStatus
from loopora.projections import replay_run_projection_bundle
from loopora.utils import utc_now


class RunEngineAdvanceStatus(StrEnum):
    RUNNING = "running"
    AWAITING_ACTOR = "awaiting_actor"
    READY_FOR_STEP = "ready_for_step"
    CLOSED = "closed"
    STOPPED = "stopped"
    FAILED = "failed"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class RunEngineAdvanceOutcome:
    run_id: str
    status: RunEngineAdvanceStatus
    snapshot: RunSnapshot
    next_action: str
    current_step_id: str | None = None
    pending_actor: ActorRef | None = None
    verdict_status: VerdictStatus = VerdictStatus.NOT_EVALUATED


@dataclass(frozen=True, slots=True)
class RunEngineIssueStepRequest:
    instruction: StepInstruction
    pending_actor: ActorRef
    correlation_id: str = ""
    causation_id: str | None = None


RunEngineClaimStepRequest = RunEngineIssueStepRequest


@dataclass(frozen=True, slots=True)
class RunEngineClaimWorkflowStepRequest:
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
class RunEngineClaimWorkflowStepResult:
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


class RepositoryRunEngine:
    """Thin transition adapter: event replay first, legacy run table fallback."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def start(self, run_id: str) -> RunEngineAdvanceOutcome:
        snapshot = self.snapshot(run_id)
        if not snapshot.state.loop_id:
            return _advance_outcome(snapshot, RunEngineAdvanceStatus.MISSING, next_action="missing")
        if snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED:
            self.repository.update_run(run_id, status="running", started_at=utc_now())
            self.rebuild_projection_cache(run_id)
            snapshot = self.snapshot(run_id)
        return _advance_outcome_for_snapshot(snapshot)

    def claim_step(self, request: RunEngineClaimStepRequest):
        instruction = request.instruction
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(instruction.run_id),
                aggregate_type="run",
                aggregate_id=instruction.run_id,
                event_type="StepInstructionIssued",
                payload={
                    **_step_instruction_payload(instruction),
                    "pending_actor": request.pending_actor.to_dict(),
                },
                actor=request.pending_actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(instruction.run_id)
        return event

    def claim_workflow_step(self, request: RunEngineClaimWorkflowStepRequest) -> RunEngineClaimWorkflowStepResult:
        instruction = workflow_step_instruction(
            WorkflowStepInstructionRequest(
                run_id=request.run_id,
                contract_ref=request.contract_ref,
                compiled_spec=request.compiled_spec,
                iteration=request.iteration,
                step=request.step,
                role=request.role,
            )
        )
        event = self.claim_step(
            RunEngineClaimStepRequest(
                instruction=instruction,
                pending_actor=request.pending_actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        return RunEngineClaimWorkflowStepResult(instruction=instruction, event=event)

    def workflow_step_index(
        self,
        run_id: str,
        *,
        workflow_steps: list[dict],
        iteration: int,
        fallback_step_index: int = 0,
    ) -> int:
        return workflow_step_index_from_events(
            WorkflowCursorFromEventsRequest(
                workflow_steps=workflow_steps,
                events=self.repository.list_domain_events(run_stream_id(run_id)),
                iteration=iteration,
                fallback_step_index=fallback_step_index,
                current_step_projection=self.current_step_projection(run_id),
            )
        )

    def issue_step_instruction(self, request: RunEngineIssueStepRequest):
        return self.claim_step(request)

    def submit_step(self, request: RunEngineSubmitStepRequest) -> RunEngineSubmitStepResult:
        result = request.result
        submitted_event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(result.run_id),
                aggregate_type="run",
                aggregate_id=result.run_id,
                event_type="StepSubmitted",
                payload={
                    "run_id": result.run_id,
                    "step_id": result.step_id,
                    "iteration": result.iteration,
                    "status": result.status.value,
                    "summary": result.summary,
                    "evidence_claim_count": len(result.evidence_claims),
                    "artifact_ref_count": len(result.artifact_refs),
                    "blocking_items": list(result.blocking_items),
                    "residual_risks": list(result.residual_risks),
                },
                actor=result.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        loop_id = self.snapshot(result.run_id).state.loop_id
        for artifact_ref in result.artifact_refs:
            self.repository.record_artifact_index(
                {
                    "run_id": result.run_id,
                    "loop_id": loop_id,
                    "kind": artifact_ref.kind,
                    "uri": artifact_ref.uri,
                    "content_hash": artifact_ref.content_hash or "",
                    "created_by_event_id": submitted_event.event_id,
                }
            )
        committed_event = self.commit_step(
            RunEngineCommitStepRequest(
                run_id=result.run_id,
                step_id=result.step_id,
                iteration=result.iteration,
                actor=result.actor,
                result_status=result.status.value,
                correlation_id=request.correlation_id,
                causation_id=submitted_event.event_id,
            )
        )
        return RunEngineSubmitStepResult(
            submitted_event=submitted_event,
            committed_event=committed_event,
        )

    def commit_step(self, request: RunEngineCommitStepRequest):
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="StepCommitted",
                payload={
                    "run_id": request.run_id,
                    "step_id": request.step_id,
                    "iteration": request.iteration,
                    "result_status": request.result_status,
                },
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def accept_evidence(self, request: RunEngineAcceptEvidenceRequest):
        evidence_entry = request.evidence_entry
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="EvidenceAccepted",
                payload=_evidence_accepted_payload(request.run_id, evidence_entry),
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def recompute_coverage(self, request: RunEngineCoverageRecomputedRequest):
        coverage = request.coverage_projection
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="CoverageRecomputed",
                payload=_coverage_recomputed_payload(request.run_id, coverage),
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def record_step_evidence(self, request: RunEngineRecordStepEvidenceRequest) -> RunEngineRecordStepEvidenceResult:
        evidence_payload = _evidence_accepted_payload(request.run_id, request.evidence_entry)
        coverage_payload = _coverage_recomputed_payload(request.run_id, request.coverage_projection)
        with self.repository.transaction() as connection:
            evidence_event = self.repository._append_domain_event_for_connection(
                connection,
                DomainEventAppendRequest(
                    stream_id=run_stream_id(request.run_id),
                    aggregate_type="run",
                    aggregate_id=request.run_id,
                    event_type="EvidenceAccepted",
                    payload=evidence_payload,
                    actor=request.actor,
                    correlation_id=request.correlation_id,
                    causation_id=request.causation_id,
                ),
            )
            coverage_event = self.repository._append_domain_event_for_connection(
                connection,
                DomainEventAppendRequest(
                    stream_id=run_stream_id(request.run_id),
                    aggregate_type="run",
                    aggregate_id=request.run_id,
                    event_type="CoverageRecomputed",
                    payload=coverage_payload,
                    actor=request.actor,
                    correlation_id=request.correlation_id or evidence_event.correlation_id,
                    causation_id=evidence_event.event_id,
                ),
            )
        self.rebuild_projection_cache(request.run_id)
        return RunEngineRecordStepEvidenceResult(
            evidence_event=evidence_event,
            coverage_event=coverage_event,
        )

    def issue_verdict(self, request: RunEngineIssueVerdictRequest):
        verdict = request.verdict
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="VerdictIssued",
                payload=_verdict_issued_payload(request.run_id, verdict),
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def start_iteration(self, request: RunEngineStartIterationRequest):
        existing = self._iteration_event(request.run_id, "IterationStarted", request.iteration)
        if existing is not None:
            return existing
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="IterationStarted",
                payload={
                    "run_id": request.run_id,
                    "iteration": request.iteration,
                    "step_count": request.step_count,
                },
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def complete_iteration(self, request: RunEngineCompleteIterationRequest):
        existing = self._iteration_event(request.run_id, "IterationCompleted", request.iteration)
        if existing is not None:
            return existing
        event = self.repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(request.run_id),
                aggregate_type="run",
                aggregate_id=request.run_id,
                event_type="IterationCompleted",
                payload={
                    "run_id": request.run_id,
                    "iteration": request.iteration,
                    "completed_step_count": request.completed_step_count,
                    "reason": request.reason,
                },
                actor=request.actor,
                correlation_id=request.correlation_id,
                causation_id=request.causation_id,
            )
        )
        self.rebuild_projection_cache(request.run_id)
        return event

    def advance(self, run_id: str) -> RunEngineAdvanceOutcome:
        snapshot = self.snapshot(run_id)
        if not snapshot.state.loop_id:
            return _advance_outcome(snapshot, RunEngineAdvanceStatus.MISSING, next_action="missing")
        if snapshot.state.lifecycle_status == RunLifecycleStatus.CREATED:
            return self.start(run_id)
        if snapshot.state.lifecycle_status in {RunLifecycleStatus.CLOSED, RunLifecycleStatus.STOPPED, RunLifecycleStatus.FAILED}:
            return _advance_outcome_for_snapshot(snapshot)
        if snapshot.verdict_status in {VerdictStatus.PASSED, VerdictStatus.PASSED_WITH_RESIDUAL_RISK}:
            self.repository.update_run(run_id, status="succeeded", finished_at=utc_now())
            self.rebuild_projection_cache(run_id)
            return _advance_outcome_for_snapshot(self.snapshot(run_id))
        return _advance_outcome_for_snapshot(snapshot)

    def replay_projections(self, run_id: str) -> dict:
        return replay_run_projection_bundle(self.repository.list_domain_events(run_stream_id(run_id)))

    def current_step_projection(self, run_id: str) -> dict:
        events = self.repository.list_domain_events(run_stream_id(run_id))
        latest_sequence = max((event.sequence for event in events), default=0)
        cached = self.repository.get_projection_record("current_step", run_id)
        payload = cached.get("payload") if isinstance(cached, dict) else {}
        cached_record_sequence = _safe_int(cached.get("source_sequence") if isinstance(cached, dict) else None, default=0)
        cached_payload_sequence = _safe_int(payload.get("source_sequence") if isinstance(payload, dict) else None, default=0)
        if (
            isinstance(payload, dict)
            and cached_record_sequence
            and cached_payload_sequence
            and cached_record_sequence >= latest_sequence
            and cached_payload_sequence >= latest_sequence
        ):
            return payload
        projections = self.rebuild_projection_cache(run_id)
        current_step = projections.get("current_step") if isinstance(projections, dict) else {}
        return current_step if isinstance(current_step, dict) else {}

    def rebuild_projection_cache(self, run_id: str) -> dict:
        return self.repository.refresh_run_projection_cache(run_id)

    def snapshot(self, run_id: str) -> RunSnapshot:
        events = self.repository.list_domain_events(run_stream_id(run_id))
        if events:
            return replay_run_snapshot(events)
        run = self.repository.get_run(run_id)
        if not run:
            return RunSnapshot(state=RunState(id=run_id, loop_id=""), latest_event_sequence=0)
        return RunSnapshot(
            state=RunState(
                id=run_id,
                loop_id=str(run.get("loop_id") or ""),
                lifecycle_status=_legacy_status_to_lifecycle(str(run.get("status") or "")),
                current_iteration=int(run.get("current_iter") or 0),
                current_step_id=None,
                pending_actor=None,
                stop_requested=bool(run.get("stop_requested")),
            ),
            latest_event_sequence=0,
            verdict_status=_legacy_task_verdict_status(run.get("task_verdict")),
        )

    def _iteration_event(self, run_id: str, event_type: str, iteration: int):
        return next(
            (
                event
                for event in self.repository.list_domain_events(run_stream_id(run_id))
                if event.event_type == event_type and _safe_int(event.payload.get("iteration"), default=-1) == iteration
            ),
            None,
        )


def _legacy_status_to_lifecycle(status: str) -> RunLifecycleStatus:
    return {
        "queued": RunLifecycleStatus.CREATED,
        "running": RunLifecycleStatus.RUNNING,
        "awaiting_agent": RunLifecycleStatus.AWAITING_ACTOR,
        "succeeded": RunLifecycleStatus.CLOSED,
        "stopped": RunLifecycleStatus.STOPPED,
        "failed": RunLifecycleStatus.FAILED,
    }.get(status, RunLifecycleStatus.CREATED)


def _legacy_task_verdict_status(value: object) -> VerdictStatus:
    if isinstance(value, dict):
        status = str(value.get("status") or "not_evaluated")
        if status == "insufficient_evidence":
            return VerdictStatus.CONTINUE_REQUIRED
        if status == "failed":
            return VerdictStatus.BLOCKED
        try:
            return VerdictStatus(status)
        except ValueError:
            return VerdictStatus.NOT_EVALUATED
    return VerdictStatus.NOT_EVALUATED


def _advance_outcome_for_snapshot(snapshot: RunSnapshot) -> RunEngineAdvanceOutcome:
    status = _advance_status_for_snapshot(snapshot)
    return _advance_outcome(snapshot, status, next_action=_next_action_for_status(status))


def _advance_status_for_snapshot(snapshot: RunSnapshot) -> RunEngineAdvanceStatus:
    lifecycle_status = snapshot.state.lifecycle_status
    if lifecycle_status == RunLifecycleStatus.CLOSED:
        return RunEngineAdvanceStatus.CLOSED
    if lifecycle_status == RunLifecycleStatus.STOPPED:
        return RunEngineAdvanceStatus.STOPPED
    if lifecycle_status == RunLifecycleStatus.FAILED:
        return RunEngineAdvanceStatus.FAILED
    if lifecycle_status == RunLifecycleStatus.AWAITING_ACTOR or snapshot.state.current_step_id:
        return RunEngineAdvanceStatus.AWAITING_ACTOR
    if lifecycle_status == RunLifecycleStatus.RUNNING:
        return RunEngineAdvanceStatus.READY_FOR_STEP
    return RunEngineAdvanceStatus.RUNNING


def _next_action_for_status(status: RunEngineAdvanceStatus) -> str:
    return {
        RunEngineAdvanceStatus.CLOSED: "complete",
        RunEngineAdvanceStatus.STOPPED: "stopped",
        RunEngineAdvanceStatus.FAILED: "failed",
        RunEngineAdvanceStatus.AWAITING_ACTOR: "await_actor_submit",
        RunEngineAdvanceStatus.READY_FOR_STEP: "claim_step",
        RunEngineAdvanceStatus.MISSING: "missing",
    }.get(status, "start")


def _advance_outcome(snapshot: RunSnapshot, status: RunEngineAdvanceStatus, *, next_action: str) -> RunEngineAdvanceOutcome:
    return RunEngineAdvanceOutcome(
        run_id=snapshot.state.id,
        status=status,
        snapshot=snapshot,
        next_action=next_action,
        current_step_id=snapshot.state.current_step_id,
        pending_actor=snapshot.state.pending_actor,
        verdict_status=snapshot.verdict_status,
    )


def _evidence_accepted_payload(run_id: str, evidence_entry: dict) -> dict:
    return {
        "run_id": run_id,
        "evidence_id": str(evidence_entry.get("id") or ""),
        "step_id": str(evidence_entry.get("step_id") or ""),
        "role_id": str(evidence_entry.get("role_id") or ""),
        "archetype": str(evidence_entry.get("archetype") or ""),
        "claim": str(evidence_entry.get("claim") or ""),
        "method": str(evidence_entry.get("method") or ""),
        "result": str(evidence_entry.get("result") or ""),
        "verifies": [str(item) for item in list(evidence_entry.get("verifies") or []) if str(item).strip()],
        "artifact_ref_count": len([item for item in list(evidence_entry.get("artifact_refs") or []) if isinstance(item, dict)]),
        "residual_risk": str(evidence_entry.get("residual_risk") or ""),
    }


def _coverage_recomputed_payload(run_id: str, coverage: dict) -> dict:
    return {
        "run_id": run_id,
        "status": str(coverage.get("status") or ""),
        "target_count": int(coverage.get("target_count") or 0),
        "covered_target_count": int(coverage.get("covered_target_count") or 0),
        "weak_target_count": int(coverage.get("weak_target_count") or 0),
        "missing_target_count": int(coverage.get("missing_target_count") or 0),
        "blocked_target_count": int(coverage.get("blocked_target_count") or 0),
        "top_gaps": [item for item in list(coverage.get("top_gaps") or []) if isinstance(item, dict)][:5],
    }


def _verdict_issued_payload(run_id: str, verdict: dict) -> dict:
    payload = {
        "run_id": run_id,
        "status": str(verdict.get("status") or "not_evaluated"),
        "source": str(verdict.get("source") or ""),
        "summary": str(verdict.get("summary") or ""),
    }
    buckets = _dict_list_payload(verdict.get("buckets"))
    if buckets:
        payload["buckets"] = buckets
    next_gap = _dict_entries(verdict.get("next_gap"))
    if next_gap:
        payload["next_gap"] = next_gap
    return payload


def _dict_list_payload(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, items in value.items():
        if not isinstance(items, list):
            continue
        result[str(key)] = _dict_entries(items)
    return result


def _dict_entries(value: object) -> list[dict]:
    return [dict(item) for item in list(value or []) if isinstance(item, dict)]


def _step_instruction_payload(instruction: StepInstruction) -> dict:
    return {
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role": asdict(instruction.role),
        "objective": instruction.objective,
        "contract_ref": instruction.contract_ref,
        "evidence_scope": asdict(instruction.evidence_scope),
        "action_policy": asdict(instruction.action_policy),
        "output_contract": asdict(instruction.output_contract),
    }


def _safe_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
