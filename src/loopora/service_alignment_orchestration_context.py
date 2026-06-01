from __future__ import annotations

from typing import Protocol

from loopora.alignment_readiness_rules import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.service_alignment_bundle_candidate import AlignmentBundleCandidateContext, handle_alignment_bundle_candidate
from loopora.service_alignment_context_protocols import AlignmentFactoryService
from loopora.service_alignment_execution import AlignmentExecutionState
from loopora.service_alignment_invocation import (
    AlignmentExecutorRunContext,
    run_alignment_executor as run_alignment_executor_command,
)
from loopora.service_alignment_orchestration import AlignmentSessionOrchestrationContext
from loopora.service_alignment_output_message import (
    AlignmentOutputMessageContext,
    AlignmentOutputMessageRequest,
    alignment_output_message_bundle_and_options,
)
from loopora.service_alignment_output_stage import (
    AlignmentOutputStageContext,
    AlignmentOutputStageRequest,
    apply_alignment_output_stage as apply_alignment_output_stage_command,
)
from loopora.service_alignment_requests import ALIGNMENT_MISSING_ITEM_IDS, ALIGNMENT_READINESS_KEYS
from loopora.service_alignment_session_lifecycle import alignment_thread_key
from loopora.service_alignment_session_state import AlignmentSessionStateContext, alignment_session_state_callbacks
from loopora.service_alignment_status import ALIGNMENT_CONFIRMED_STAGES
from loopora.service_alignment_transcript import (
    AlignmentAssistantMessageEffect,
    AlignmentTranscriptContext,
    record_alignment_assistant_message,
)
from loopora.utils import utc_now


class AlignmentOrchestrationContextProvider(Protocol):
    def executor_run_context(self) -> AlignmentExecutorRunContext: ...

    def output_stage_context(self) -> AlignmentOutputStageContext: ...

    def output_message_context(self) -> AlignmentOutputMessageContext: ...

    def bundle_candidate_context(self) -> AlignmentBundleCandidateContext: ...

    def transcript_context(self) -> AlignmentTranscriptContext: ...

    def session_state_context(self) -> AlignmentSessionStateContext: ...


def alignment_session_orchestration_context(
    service: AlignmentFactoryService,
    provider: AlignmentOrchestrationContextProvider,
) -> AlignmentSessionOrchestrationContext:
    state_callbacks = alignment_session_state_callbacks(provider.session_state_context())

    def run_executor(
        session_id: str,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> dict:
        return run_alignment_executor_command(
            provider.executor_run_context(),
            session_id,
            mode=mode,
            validation_error=validation_error,
            invalid_yaml=invalid_yaml,
        )

    def apply_output_stage(session_id: str, session: dict, output: dict) -> dict:
        return apply_alignment_output_stage_command(
            provider.output_stage_context(),
            AlignmentOutputStageRequest(
                session_id=session_id,
                session=session,
                output=output,
                readiness_keys=ALIGNMENT_READINESS_KEYS,
                readiness_evidence_keys=list(ALIGNMENT_READINESS_EVIDENCE_KEYS),
            ),
        )

    def handle_bundle_candidate_callback(session_id: str, bundle_yaml: str) -> AlignmentExecutionState | None:
        return handle_alignment_bundle_candidate(provider.bundle_candidate_context(), session_id, bundle_yaml)

    def record_assistant_message_callback(
        session_id: str,
        session: dict,
        assistant_message: str,
        *,
        decision_options: list[dict] | None = None,
        missing_items: list[str] | None = None,
    ) -> None:
        record_alignment_assistant_message(
            provider.transcript_context(),
            session_id,
            AlignmentAssistantMessageEffect(
                session=session,
                message=assistant_message,
                created_at=utc_now(),
                decision_options=decision_options,
                missing_items=missing_items,
            ),
        )

    def output_message_bundle_and_options(
        session_id: str,
        session: dict,
        output: dict,
    ) -> tuple[str, str, list[dict], list[str] | None]:
        result = alignment_output_message_bundle_and_options(
            provider.output_message_context(),
            AlignmentOutputMessageRequest(
                session_id=session_id,
                session=session,
                output=output,
                confirmed_stages=ALIGNMENT_CONFIRMED_STAGES,
                missing_item_ids=ALIGNMENT_MISSING_ITEM_IDS,
                readiness_keys=ALIGNMENT_READINESS_KEYS,
                readiness_evidence_keys=list(ALIGNMENT_READINESS_EVIDENCE_KEYS),
            ),
        )
        return result.assistant_message, result.bundle_yaml, result.decision_options, result.missing_items

    return AlignmentSessionOrchestrationContext(
        repository=service.repository,
        get_session=service.get_alignment_session,
        run_executor=run_executor,
        apply_output_stage=apply_output_stage,
        output_message_bundle_and_options=output_message_bundle_and_options,
        record_assistant_message=record_assistant_message_callback,
        handle_bundle_candidate=handle_bundle_candidate_callback,
        apply_transition_plan=state_callbacks.apply_transition_plan,
        fail_session=state_callbacks.fail_session,
        threads=service._threads,
        thread_key=alignment_thread_key,
    )
