from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from loopora.alignment_readiness_rules import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.diagnostics import get_logger
from loopora.service_alignment_artifacts import (
    alignment_next_invocation_dir,
    alignment_repair_attempts,
    ensure_alignment_artifact_dirs,
    write_alignment_validation_log,
)
from loopora.service_alignment_diagnostics import (
    append_alignment_diagnostic_event,
    append_alignment_local_diagnostic_event,
    log_alignment_diagnostic_event_failure,
)
from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
)
from loopora.service_alignment_bundle_preview import AlignmentBundlePreviewContext, alignment_bundle_preview
from loopora.service_alignment_bundle_candidate import AlignmentBundleCandidateContext, handle_alignment_bundle_candidate
from loopora.service_alignment_transcript import (
    AlignmentAssistantMessageEffect,
    AlignmentTranscriptContext,
    localized_alignment_system_message_appender,
    record_alignment_assistant_message,
)
from loopora.service_alignment_execution import AlignmentExecutionState
from loopora.service_alignment_invocation import (
    AlignmentExecutorInvocationConfig,
    AlignmentExecutorRunContext,
    run_alignment_executor as run_alignment_executor_command,
)
from loopora.service_alignment_output_stage import (
    AlignmentOutputStageContext,
    AlignmentOutputStageRequest,
    apply_alignment_output_stage as apply_alignment_output_stage_command,
)
from loopora.service_alignment_context import (
    alignment_bundle_revision_source_context,
    alignment_run_artifact_paths,
    alignment_run_coverage_summary,
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
    alignment_run_revision_source_context,
    alignment_revision_seed_bundle,
    alignment_same_workdir,
    redact_alignment_source_value,
)
from loopora.service_alignment_delete import AlignmentDeleteContext, delete_alignment_session as delete_alignment_session_command
from loopora.service_alignment_legacy import AlignmentLegacyLayoutContext, ensure_alignment_session_layout
from loopora.service_alignment_prompting import (
    AlignmentPromptBuildContext,
    build_alignment_prompt as build_alignment_prompt_command,
)
from loopora.service_alignment_run_recovery import (
    agent_recovery_agent_entry_candidate_event,
    agent_recovery_agent_entry_ready_event,
    agent_recovery_session_has_candidate_yaml,
)
from loopora.service_alignment_run_context import AlignmentRunContextResolverContext, resolve_alignment_run_context
from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolutionRequest,
    AlignmentLooporaContextResolverContext,
    AlignmentWorkdirContextResolverContext,
    alignment_workdir_context_payload,
    get_alignment_workdir_context as get_alignment_workdir_context_command,
    resolve_plan_context_from_workdir_context,
    resolve_loopora_context as resolve_loopora_context_command,
)
from loopora.service_alignment_requests import (
    ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
    ALIGNMENT_MISSING_ITEM_IDS,
    ALIGNMENT_READINESS_KEYS,
    ALIGNMENT_RESPONSE_SCHEMA,
    AlignmentSessionCreateRequest,
    RevisionAlignmentSessionRequest,
    RevisionSessionOptions,
    coerce_alignment_session_create_request,
    coerce_revision_session_options,
)
from loopora.service_alignment_revision import (
    AlignmentRevisionContext,
    create_revision_alignment_session as create_revision_alignment_session_command,
)
from loopora.service_alignment_import import AlignmentImportContext, import_alignment_bundle as import_alignment_bundle_command
from loopora.service_alignment_message import AlignmentMessageContext, append_alignment_message as append_alignment_message_command
from loopora.service_alignment_sync import AlignmentSyncContext, sync_alignment_bundle_from_file as sync_alignment_bundle_from_file_command
from loopora.service_alignment_source_lookup import alignment_run_source_bundle, resolve_alignment_source_option_seed
from loopora.service_alignment_output_message import (
    AlignmentOutputMessageContext,
    AlignmentOutputMessageRequest,
    alignment_output_message_bundle_and_options,
)
from loopora.service_alignment_session_state import (
    AlignmentSessionStateContext,
    alignment_session_state_callbacks,
)
from loopora.service_alignment_session_creation import (
    AlignmentSessionCreationContext,
    alignment_session_dir,
    create_alignment_session as create_alignment_session_command,
)
from loopora.service_alignment_session_projection import (
    AlignmentSessionAccessContext,
    decorate_alignment_session,
    get_alignment_session as get_alignment_session_command,
    latest_alignment_event_id as latest_alignment_event_id_command,
    list_alignment_events as list_alignment_events_command,
    list_alignment_sessions as list_alignment_sessions_command,
)
from loopora.service_alignment_session_lifecycle import (
    AlignmentSessionLifecycleContext,
    alignment_thread_key,
    cancel_alignment_session as cancel_alignment_session_lifecycle,
    start_alignment_session_async as start_alignment_session_lifecycle,
)
from loopora.service_alignment_orchestration import AlignmentSessionOrchestrationContext, execute_alignment_session
from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES, ALIGNMENT_CONFIRMED_STAGES
from loopora.service_alignment_validation import AlignmentBundleTextValidationContext, alignment_validated_bundle_text_loader
from loopora.utils import utc_now

logger = get_logger(__name__)

class ServiceAlignmentMixin:
    def create_alignment_session(
        self,
        request: AlignmentSessionCreateRequest | None = None,
        **raw_request: object,
    ) -> dict:
        request = coerce_alignment_session_create_request(request, raw_request)
        return create_alignment_session_command(self._alignment_session_creation_context(), request)

    def get_alignment_session(self, session_id: str) -> dict:
        return get_alignment_session_command(self._alignment_session_access_context(), session_id)

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        return list_alignment_sessions_command(self._alignment_session_access_context(), limit=limit)

    def delete_alignment_session(self, session_id: str) -> bool:
        return delete_alignment_session_command(
            self._alignment_delete_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            logger=logger,
        )

    def _append_alignment_diagnostic_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        return append_alignment_diagnostic_event(self, logger, session_id, event_type, payload)

    def _append_alignment_local_diagnostic_event(self, session: dict, event_type: str, payload: dict) -> None:
        append_alignment_local_diagnostic_event(self, logger, session, event_type, payload)

    @staticmethod
    def _log_alignment_diagnostic_event_failure(
        *,
        session_id: str,
        event_type: str,
        payload: dict,
        error: BaseException,
    ) -> None:
        log_alignment_diagnostic_event_failure(
            logger,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
            error=error,
        )

    def append_alignment_message(self, session_id: str, message: str) -> dict:
        return append_alignment_message_command(
            self._alignment_message_context(),
            session_id,
            message,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            confirmed_stages=ALIGNMENT_CONFIRMED_STAGES,
        )

    def start_alignment_session_async(self, session_id: str) -> None:
        start_alignment_session_lifecycle(
            self._alignment_session_lifecycle_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
        )

    def cancel_alignment_session(self, session_id: str) -> dict:
        return cancel_alignment_session_lifecycle(
            self._alignment_session_lifecycle_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            logger=logger,
        )

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        return list_alignment_events_command(
            self._alignment_session_access_context(),
            session_id,
            after_id=after_id,
            limit=limit,
        )

    def latest_alignment_event_id(self, session_id: str) -> int:
        return latest_alignment_event_id_command(self._alignment_session_access_context(), session_id)

    def get_alignment_workdir_context(self, workdir: Path) -> dict:
        return get_alignment_workdir_context_command(self._alignment_loopora_context_resolver_context(), workdir)

    def resolve_loopora_context(
        self,
        workdir: Path,
        *,
        intent: str = "plan",
        adapter: str = "",
        context_id: str = "",
        source_option_id: str = "",
    ) -> dict:
        return resolve_loopora_context_command(
            self._alignment_loopora_context_resolver_context(),
            workdir,
            AlignmentLooporaContextResolutionRequest(
                intent=intent,
                adapter=adapter,
                context_id=context_id,
                source_option_id=source_option_id,
            ),
        )

    def get_alignment_bundle(self, session_id: str) -> dict:
        return alignment_bundle_preview(self._alignment_bundle_preview_context(), self.get_alignment_session(session_id))

    def _ensure_alignment_session_layout(self, session: dict) -> dict:
        return ensure_alignment_session_layout(
            AlignmentLegacyLayoutContext(
                repository=self.repository,
                ensure_artifact_dirs=ensure_alignment_artifact_dirs,
                append_diagnostic_event=self._append_alignment_diagnostic_event,
            ),
            session,
        )

    def _alignment_bundle_lifecycle_context(self) -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            write_validation_log=write_alignment_validation_log,
        )

    def _alignment_bundle_preview_context(self) -> AlignmentBundlePreviewContext:
        return AlignmentBundlePreviewContext(
            build_preview=self._bundle_preview_payload,
            load_validated_bundle_text=self._alignment_bundle_text_loader(),
        )

    def _alignment_bundle_candidate_context(self) -> AlignmentBundleCandidateContext:
        state_callbacks = alignment_session_state_callbacks(self._alignment_session_state_context())
        return AlignmentBundleCandidateContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            load_validated_bundle_text=self._alignment_bundle_text_loader(),
            bundle_lifecycle_context=self._alignment_bundle_lifecycle_context,
            apply_transition_plan=state_callbacks.apply_transition_plan,
            fail_session=state_callbacks.fail_session,
        )

    def _alignment_session_state_context(self) -> AlignmentSessionStateContext:
        return AlignmentSessionStateContext(repository=self.repository)

    def _alignment_session_access_context(self) -> AlignmentSessionAccessContext:
        return AlignmentSessionAccessContext(
            repository=self.repository,
            ensure_session_layout=self._ensure_alignment_session_layout,
            candidate_event=lambda session_id: agent_recovery_agent_entry_candidate_event(self.repository, session_id),
            ready_event=lambda session_id: agent_recovery_agent_entry_ready_event(self.repository, session_id),
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            missing_judgment_item_ids=ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
        )

    def _alignment_output_stage_context(self) -> AlignmentOutputStageContext:
        return AlignmentOutputStageContext(
            repository=self.repository,
            decorate_session=lambda session: decorate_alignment_session(
                session,
                active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            ),
        )

    def _alignment_output_message_context(self) -> AlignmentOutputMessageContext:
        return AlignmentOutputMessageContext(repository=self.repository)

    def _alignment_executor_run_context(self) -> AlignmentExecutorRunContext:
        def build_prompt(
            session: dict,
            *,
            mode: str,
            validation_error: str = "",
            invalid_yaml: str = "",
        ) -> str:
            return build_alignment_prompt_command(
                AlignmentPromptBuildContext(),
                session,
                mode=mode,
                validation_error=validation_error,
                invalid_yaml=invalid_yaml,
            )

        return AlignmentExecutorRunContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            config=AlignmentExecutorInvocationConfig(
                output_schema=ALIGNMENT_RESPONSE_SCHEMA,
                idle_timeout_seconds=self.settings.role_idle_timeout_seconds,
                executor_factory=self.executor_factory,
                build_prompt=build_prompt,
                ensure_artifact_dirs=ensure_alignment_artifact_dirs,
                next_invocation_dir=alignment_next_invocation_dir,
                repair_attempts=alignment_repair_attempts,
            ),
        )

    def _alignment_session_creation_context(self) -> AlignmentSessionCreationContext:
        return AlignmentSessionCreationContext(
            repository=self.repository,
            resolve_source_seed=lambda workdir, source_option_id: resolve_alignment_source_option_seed(
                self,
                workdir,
                source_option_id,
            ),
            session_dir=alignment_session_dir,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            get_session=self.get_alignment_session,
            start_session_async=self.start_alignment_session_async,
        )

    def _alignment_revision_context(self) -> AlignmentRevisionContext:
        return AlignmentRevisionContext(
            repository=self.repository,
            create_session=self.create_alignment_session,
            get_session=self.get_alignment_session,
            start_session_async=self.start_alignment_session_async,
            redact_source_value=redact_alignment_source_value,
        )

    def _alignment_import_context(self, session_id: str) -> AlignmentImportContext:
        return AlignmentImportContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            has_agent_entry_candidate=lambda candidate_session_id: bool(
                agent_recovery_agent_entry_candidate_event(self.repository, candidate_session_id)
            ),
            load_validated_bundle_text=self._alignment_bundle_text_loader(),
            import_bundle_text=lambda bundle_yaml: self.import_bundle_text(
                bundle_yaml,
                imported_from_path=str(Path(self.get_alignment_session(session_id)["bundle_path"])),
            ),
            start_run=self.start_run,
            start_run_async=self.start_run_async,
            bundle_lifecycle_context=self._alignment_bundle_lifecycle_context,
        )

    def _alignment_message_context(self) -> AlignmentMessageContext:
        return AlignmentMessageContext(
            get_session=self.get_alignment_session,
            transcript_context=self._alignment_transcript_context,
            start_session_async=self.start_alignment_session_async,
        )

    def _alignment_delete_context(self) -> AlignmentDeleteContext:
        return AlignmentDeleteContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            append_local_diagnostic_event=self._append_alignment_local_diagnostic_event,
            mark_local_asset_cleanup_by_path=self._mark_local_asset_cleanup_by_path,
        )

    def _alignment_sync_context(self) -> AlignmentSyncContext:
        return AlignmentSyncContext(
            get_session=self.get_alignment_session,
            load_validated_bundle_text=self._alignment_bundle_text_loader(),
            append_system_message=localized_alignment_system_message_appender(self._alignment_transcript_context()),
            bundle_lifecycle_context=self._alignment_bundle_lifecycle_context,
            build_preview=self._bundle_preview_payload,
        )

    def _alignment_bundle_text_loader(self) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
        return alignment_validated_bundle_text_loader(
            AlignmentBundleTextValidationContext(
                has_agent_candidate_yaml=lambda session_id: agent_recovery_session_has_candidate_yaml(
                    self.repository,
                    session_id,
                ),
            )
        )

    def _alignment_session_lifecycle_context(self) -> AlignmentSessionLifecycleContext:
        def execute_session(session_id: str) -> None:
            execute_alignment_session(
                self._alignment_session_orchestration_context(),
                session_id,
                logger=logger,
            )

        return AlignmentSessionLifecycleContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
            execute_session=execute_session,
            threads=self._threads,
            thread_key=alignment_thread_key,
            append_diagnostic_event=self._append_alignment_diagnostic_event,
            signal_process=os.kill,
        )

    def _alignment_session_orchestration_context(self) -> AlignmentSessionOrchestrationContext:
        state_callbacks = alignment_session_state_callbacks(self._alignment_session_state_context())

        def run_executor(
            session_id: str,
            *,
            mode: str,
            validation_error: str = "",
            invalid_yaml: str = "",
        ) -> dict:
            return run_alignment_executor_command(
                self._alignment_executor_run_context(),
                session_id,
                mode=mode,
                validation_error=validation_error,
                invalid_yaml=invalid_yaml,
            )

        def apply_output_stage(session_id: str, session: dict, output: dict) -> dict:
            return apply_alignment_output_stage_command(
                self._alignment_output_stage_context(),
                AlignmentOutputStageRequest(
                    session_id=session_id,
                    session=session,
                    output=output,
                    readiness_keys=ALIGNMENT_READINESS_KEYS,
                    readiness_evidence_keys=list(ALIGNMENT_READINESS_EVIDENCE_KEYS),
                ),
            )

        def handle_bundle_candidate_callback(session_id: str, bundle_yaml: str) -> AlignmentExecutionState | None:
            return handle_alignment_bundle_candidate(self._alignment_bundle_candidate_context(), session_id, bundle_yaml)

        def record_assistant_message_callback(
            session_id: str,
            session: dict,
            assistant_message: str,
            *,
            decision_options: list[dict] | None = None,
            missing_items: list[str] | None = None,
        ) -> None:
            record_alignment_assistant_message(
                self._alignment_transcript_context(),
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
                self._alignment_output_message_context(),
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
            repository=self.repository,
            get_session=self.get_alignment_session,
            run_executor=run_executor,
            apply_output_stage=apply_output_stage,
            output_message_bundle_and_options=output_message_bundle_and_options,
            record_assistant_message=record_assistant_message_callback,
            handle_bundle_candidate=handle_bundle_candidate_callback,
            apply_transition_plan=state_callbacks.apply_transition_plan,
            fail_session=state_callbacks.fail_session,
            threads=self._threads,
            thread_key=alignment_thread_key,
        )

    def _alignment_transcript_context(self) -> AlignmentTranscriptContext:
        return AlignmentTranscriptContext(
            repository=self.repository,
            get_session=self.get_alignment_session,
        )

    def _alignment_run_context_resolver_context(self) -> AlignmentRunContextResolverContext:
        return AlignmentRunContextResolverContext(
            repository=self.repository,
            get_alignment_session=self.get_alignment_session,
            get_run=self.get_run,
            same_workdir=alignment_same_workdir,
        )

    def _alignment_workdir_context_resolver_context(self) -> AlignmentWorkdirContextResolverContext:
        return AlignmentWorkdirContextResolverContext(
            repository=self.repository,
            list_loops=self.list_loops,
            get_run=self.get_run,
        )

    def _alignment_loopora_context_resolver_context(self) -> AlignmentLooporaContextResolverContext:
        def workdir_context_payload(root: Path) -> dict:
            return alignment_workdir_context_payload(self._alignment_workdir_context_resolver_context(), root)

        def resolve_plan_context(context: dict, *, source_option_id: str = "") -> dict:
            return resolve_plan_context_from_workdir_context(context, source_option_id=source_option_id)

        def resolve_run_context(root: Path, *, adapter: str, context_id: str) -> dict:
            return resolve_alignment_run_context(
                self._alignment_run_context_resolver_context(),
                root=root,
                adapter=adapter,
                context_id=context_id,
            )

        return AlignmentLooporaContextResolverContext(
            workdir_context_payload=workdir_context_payload,
            resolve_plan_context=resolve_plan_context,
            resolve_run_context=resolve_run_context,
        )

    def sync_alignment_bundle_from_file(self, session_id: str) -> dict:
        return sync_alignment_bundle_from_file_command(
            self._alignment_sync_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
        )

    def import_alignment_bundle(self, session_id: str, *, start_immediately: bool = True, execute_async: bool = True) -> dict:
        return import_alignment_bundle_command(
            self._alignment_import_context(session_id),
            session_id,
            start_immediately=start_immediately,
            execute_async=execute_async,
        )

    def create_bundle_revision_session(
        self,
        bundle_id: str,
        request: RevisionSessionOptions | None = None,
        **raw_request: object,
    ) -> dict:
        request = coerce_revision_session_options(request, raw_request)
        source_bundle = self.export_bundle(bundle_id)
        seed_bundle = alignment_revision_seed_bundle(source_bundle)
        return create_revision_alignment_session_command(
            self._alignment_revision_context(),
            RevisionAlignmentSessionRequest(
                seed_bundle=seed_bundle,
                message=request.message or "请先阅读这份已有 Loop 方案，和我对话改进它。先指出你需要确认的最小问题，不要直接生成。",
                start_immediately=request.start_immediately,
                source_context=alignment_bundle_revision_source_context(bundle_id, source_bundle),
                linked_bundle_id=bundle_id,
                linked_run_id="",
                executor_settings=request.executor_settings,
            )
        )

    def create_run_revision_session(
        self,
        run_id: str,
        request: RevisionSessionOptions | None = None,
        **raw_request: object,
    ) -> dict:
        request = coerce_revision_session_options(request, raw_request)
        run = self.get_run(run_id)
        loop = self.get_loop(run["loop_id"])
        source_bundle_id, source_bundle = alignment_run_source_bundle(
            self,
            run,
            loop,
            fallback_description="Derived as the improvement base for a run without an imported bundle.",
        )
        seed_bundle = alignment_revision_seed_bundle(source_bundle)
        return create_revision_alignment_session_command(
            self._alignment_revision_context(),
            RevisionAlignmentSessionRequest(
                seed_bundle=seed_bundle,
                message=request.message or "请基于这次运行的证据和守门裁决，和我对话改进 Loop 方案。先说明最可能要改的治理点，再问我最小必要问题。",
                start_immediately=request.start_immediately,
                source_context=alignment_run_revision_source_context(
                    run_id,
                    run,
                    source_bundle,
                    source_bundle_id=source_bundle_id,
                    artifact_paths=alignment_run_artifact_paths(run),
                    judgment_contract=alignment_run_judgment_contract(run),
                    coverage_summary=alignment_run_coverage_summary(run),
                    evidence_summary=alignment_run_evidence_summary(run),
                ),
                linked_bundle_id=source_bundle_id,
                linked_run_id=run_id,
                executor_settings=request.executor_settings,
            )
        )

    @staticmethod
    def _ensure_alignment_artifact_dirs(root: Path) -> None:
        ensure_alignment_artifact_dirs(root)
