from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import os
from pathlib import Path

from loopora.service_alignment_artifacts import ensure_alignment_artifact_dirs, write_alignment_validation_log
from loopora.service_alignment_bundle_candidate import AlignmentBundleCandidateContext
from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_bundle_preview import AlignmentBundlePreviewContext
from loopora.service_alignment_context_protocols import AlignmentFactoryService
from loopora.service_alignment_context_resolution_factory import (
    alignment_loopora_context_resolver_context as build_alignment_loopora_context_resolver_context,
    alignment_run_context_resolver_context as build_alignment_run_context_resolver_context,
    alignment_workdir_context_resolver_context as build_alignment_workdir_context_resolver_context,
)
from loopora.service_alignment_executor_context import alignment_executor_run_context
from loopora.service_alignment_source_context import redact_alignment_source_value
from loopora.service_alignment_delete import AlignmentDeleteContext
from loopora.service_alignment_import import AlignmentImportContext
from loopora.service_alignment_invocation import AlignmentExecutorRunContext
from loopora.service_alignment_message import AlignmentMessageContext
from loopora.service_alignment_orchestration import AlignmentSessionOrchestrationContext, execute_alignment_session
from loopora.service_alignment_orchestration_context import alignment_session_orchestration_context
from loopora.service_alignment_output_message import (
    AlignmentOutputMessageContext,
)
from loopora.service_alignment_output_stage import (
    AlignmentOutputStageContext,
)
from loopora.service_alignment_requests import (
    ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
)
from loopora.service_alignment_recovery import (
    AlignmentRecoveryContext,
    alignment_process_exists,
)
from loopora.service_alignment_revision import AlignmentRevisionContext
from loopora.service_alignment_run_context import AlignmentRunContextResolverContext
from loopora.service_alignment_run_recovery import (
    agent_recovery_agent_entry_candidate_event,
    agent_recovery_agent_entry_ready_event,
)
from loopora.service_alignment_session_creation import AlignmentSessionCreationContext, alignment_session_dir
from loopora.service_alignment_session_lifecycle import AlignmentSessionLifecycleContext, alignment_thread_key
from loopora.service_alignment_session_layout_context import (
    append_alignment_service_diagnostic_event,
    append_alignment_service_local_diagnostic_event,
    ensure_alignment_session_layout_from_service,
)
from loopora.service_alignment_session_projection import (
    AlignmentSessionAccessContext,
    decorate_alignment_session,
    get_alignment_session as get_alignment_session_command,
)
from loopora.service_alignment_session_state import AlignmentSessionStateContext, alignment_session_state_callbacks
from loopora.service_alignment_source_lookup import alignment_run_source_bundle, resolve_alignment_source_option_seed
from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES
from loopora.service_alignment_sync import AlignmentSyncContext
from loopora.service_alignment_transcript import (
    AlignmentTranscriptContext,
    alignment_notice_appender,
)
from loopora.service_alignment_validation import AlignmentBundleTextValidationContext, alignment_validated_bundle_text_loader
from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolverContext,
    AlignmentWorkdirContextResolverContext,
)


@dataclass(frozen=True, slots=True)
class AlignmentServiceContextFactory:
    service: AlignmentFactoryService
    logger: logging.Logger

    def ensure_session_layout(self, session: dict) -> dict:
        return ensure_alignment_session_layout_from_service(self.service, self.logger, session)

    def append_diagnostic_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        return append_alignment_service_diagnostic_event(self.service, self.logger, session_id, event_type, payload)

    def append_local_diagnostic_event(self, session: dict, event_type: str, payload: dict) -> None:
        append_alignment_service_local_diagnostic_event(self.logger, session, event_type, payload)

    def bundle_lifecycle_context(self) -> AlignmentBundleLifecycleContext:
        service = self.service
        return AlignmentBundleLifecycleContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            write_validation_log=write_alignment_validation_log,
        )

    def bundle_preview_context(self) -> AlignmentBundlePreviewContext:
        service = self.service
        return AlignmentBundlePreviewContext(
            build_preview=service._bundle_preview_payload,
            load_validated_bundle_text=self.bundle_text_loader(),
        )

    def bundle_candidate_context(self) -> AlignmentBundleCandidateContext:
        service = self.service
        state_callbacks = alignment_session_state_callbacks(self.session_state_context())
        return AlignmentBundleCandidateContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            load_validated_bundle_text=self.bundle_text_loader(),
            bundle_lifecycle_context=self.bundle_lifecycle_context,
            apply_transition_plan=state_callbacks.apply_transition_plan,
            fail_session=state_callbacks.fail_session,
        )

    def session_state_context(self) -> AlignmentSessionStateContext:
        return AlignmentSessionStateContext(repository=self.service.repository)

    def session_access_context(self) -> AlignmentSessionAccessContext:
        service = self.service
        return AlignmentSessionAccessContext(
            repository=service.repository,
            ensure_session_layout=self.ensure_session_layout,
            candidate_event=lambda session_id: agent_recovery_agent_entry_candidate_event(service.repository, session_id),
            ready_event=lambda session_id: agent_recovery_agent_entry_ready_event(service.repository, session_id),
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            missing_judgment_item_ids=ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
        )

    def output_stage_context(self) -> AlignmentOutputStageContext:
        service = self.service
        return AlignmentOutputStageContext(
            repository=service.repository,
            decorate_session=lambda session: decorate_alignment_session(
                session,
                active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            ),
        )

    def output_message_context(self) -> AlignmentOutputMessageContext:
        return AlignmentOutputMessageContext(repository=self.service.repository)

    def executor_run_context(self) -> AlignmentExecutorRunContext:
        return alignment_executor_run_context(self.service)

    def session_creation_context(self) -> AlignmentSessionCreationContext:
        service = self.service
        return AlignmentSessionCreationContext(
            repository=service.repository,
            resolve_source_seed=lambda workdir, source_option_id: resolve_alignment_source_option_seed(
                service,
                workdir,
                source_option_id,
            ),
            session_dir=alignment_session_dir,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            get_session=service.get_alignment_session,
            start_session_async=service.start_alignment_session_async,
        )

    def revision_context(self) -> AlignmentRevisionContext:
        service = self.service
        return AlignmentRevisionContext(
            repository=service.repository,
            create_session=service.create_alignment_session,
            get_session=service.get_alignment_session,
            export_bundle=service.export_bundle,
            get_run=service.get_run,
            get_loop=service.get_loop,
            run_source_bundle=lambda run, loop: alignment_run_source_bundle(
                service,
                run,
                loop,
                fallback_description="Derived as the improvement base for a run without an imported bundle.",
            ),
            start_session_async=service.start_alignment_session_async,
            redact_source_value=redact_alignment_source_value,
        )

    def import_context(self, session_id: str) -> AlignmentImportContext:
        service = self.service
        return AlignmentImportContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            has_agent_entry_candidate=lambda candidate_session_id: bool(
                agent_recovery_agent_entry_candidate_event(service.repository, candidate_session_id)
            ),
            load_validated_bundle_text=self.bundle_text_loader(),
            import_bundle_text=lambda bundle_yaml: service.import_bundle_text(
                bundle_yaml,
                imported_from_path=str(Path(service.get_alignment_session(session_id)["bundle_path"])),
            ),
            start_run=service.start_run,
            start_run_async=service.start_run_async,
            bundle_lifecycle_context=self.bundle_lifecycle_context,
        )

    def message_context(self) -> AlignmentMessageContext:
        service = self.service
        return AlignmentMessageContext(
            get_session=service.get_alignment_session,
            transcript_context=self.transcript_context,
            start_session_async=service.start_alignment_session_async,
        )

    def delete_context(self) -> AlignmentDeleteContext:
        service = self.service
        return AlignmentDeleteContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            append_local_diagnostic_event=self.append_local_diagnostic_event,
            mark_local_asset_cleanup_by_path=service._mark_local_asset_cleanup_by_path,
        )

    def sync_context(self) -> AlignmentSyncContext:
        service = self.service
        return AlignmentSyncContext(
            get_session=service.get_alignment_session,
            load_validated_bundle_text=self.sync_bundle_text_loader(),
            append_notice_message=alignment_notice_appender(self.transcript_context()),
            bundle_lifecycle_context=self.bundle_lifecycle_context,
            build_preview=service._bundle_preview_payload,
        )

    def bundle_text_loader(self) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
        return alignment_validated_bundle_text_loader(AlignmentBundleTextValidationContext())

    def sync_bundle_text_loader(self) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
        service = self.service

        def load_bundle(session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
            candidate_event = agent_recovery_agent_entry_candidate_event(service.repository, str(session.get("id") or ""))
            payload = candidate_event.get("payload") if isinstance(candidate_event.get("payload"), dict) else {}
            has_agent_candidate_yaml = payload.get("has_candidate_yaml") is True
            context = AlignmentBundleTextValidationContext(
                include_agent_candidate_loop_fit_contradiction=has_agent_candidate_yaml,
                include_agent_candidate_contract_issues=has_agent_candidate_yaml,
            )
            return alignment_validated_bundle_text_loader(context)(session, bundle_yaml, semantic_issues)

        return load_bundle

    def session_lifecycle_context(self) -> AlignmentSessionLifecycleContext:
        service = self.service

        def execute_session(session_id: str) -> None:
            execute_alignment_session(
                self.session_orchestration_context(),
                session_id,
                logger=self.logger,
            )

        return AlignmentSessionLifecycleContext(
            repository=service.repository,
            get_session=lambda session_id: get_alignment_session_command(self.session_access_context(), session_id),
            execute_session=execute_session,
            threads=service._threads,
            thread_key=alignment_thread_key,
            append_diagnostic_event=self.append_diagnostic_event,
            signal_process=os.kill,
        )

    def recovery_context(self) -> AlignmentRecoveryContext:
        service = self.service
        settings = service.settings
        grace_seconds = max(
            float(settings.stop_grace_period_seconds or 0.0),
            float(settings.polling_interval_seconds or 0.0) * 4,
            30.0,
        )
        return AlignmentRecoveryContext(
            repository=service.repository,
            threads=service._threads,
            thread_key=alignment_thread_key,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            orphan_grace_seconds=grace_seconds,
            pid_exists=alignment_process_exists,
        )

    def session_orchestration_context(self) -> AlignmentSessionOrchestrationContext:
        return alignment_session_orchestration_context(self.service, self)

    def transcript_context(self) -> AlignmentTranscriptContext:
        service = self.service
        return AlignmentTranscriptContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
        )

    def run_context_resolver_context(self) -> AlignmentRunContextResolverContext:
        return build_alignment_run_context_resolver_context(self.service)

    def workdir_context_resolver_context(self) -> AlignmentWorkdirContextResolverContext:
        return build_alignment_workdir_context_resolver_context(self.service)

    def loopora_context_resolver_context(self) -> AlignmentLooporaContextResolverContext:
        return build_alignment_loopora_context_resolver_context(self.service)
