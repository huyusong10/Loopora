from __future__ import annotations

from pathlib import Path

from loopora.diagnostics import get_logger
from loopora.service_alignment_bundle_preview import alignment_bundle_preview
from loopora.service_alignment_context_factory import AlignmentServiceContextFactory
from loopora.service_alignment_delete import delete_alignment_session as delete_alignment_session_command
from loopora.service_alignment_import import import_alignment_bundle as import_alignment_bundle_command
from loopora.service_alignment_message import append_alignment_message as append_alignment_message_command
from loopora.service_alignment_requests import (
    AlignmentSessionCreateRequest,
    RevisionSessionOptions,
    coerce_alignment_session_create_request,
    coerce_revision_session_options,
)
from loopora.service_alignment_revision import (
    create_bundle_revision_alignment_session as create_bundle_revision_alignment_session_command,
    create_run_revision_alignment_session as create_run_revision_alignment_session_command,
)
from loopora.service_alignment_session_creation import create_alignment_session as create_alignment_session_command
from loopora.service_alignment_session_lifecycle import (
    cancel_alignment_session as cancel_alignment_session_lifecycle,
    start_alignment_session_async as start_alignment_session_lifecycle,
    start_alignment_session_sync as start_alignment_session_sync_lifecycle,
)
from loopora.service_alignment_session_projection import (
    get_alignment_session as get_alignment_session_command,
    latest_alignment_event_id as latest_alignment_event_id_command,
    list_alignment_events as list_alignment_events_command,
    list_alignment_sessions as list_alignment_sessions_command,
)
from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES, ALIGNMENT_CONFIRMED_STAGES
from loopora.service_alignment_sync import sync_alignment_bundle_from_file as sync_alignment_bundle_from_file_command
from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolutionRequest,
    get_alignment_workdir_context as get_alignment_workdir_context_command,
    resolve_loopora_context as resolve_loopora_context_command,
)

logger = get_logger(__name__)


class ServiceAlignmentMixin:
    def create_alignment_session(
        self,
        request: AlignmentSessionCreateRequest | None = None,
        **raw_request: object,
    ) -> dict:
        request = coerce_alignment_session_create_request(request, raw_request)
        return create_alignment_session_command(self._alignment_context_factory().session_creation_context(), request)

    def get_alignment_session(self, session_id: str) -> dict:
        return get_alignment_session_command(self._alignment_context_factory().session_access_context(), session_id)

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        return list_alignment_sessions_command(self._alignment_context_factory().session_access_context(), limit=limit)

    def delete_alignment_session(self, session_id: str) -> bool:
        return delete_alignment_session_command(
            self._alignment_context_factory().delete_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            logger=logger,
        )

    def append_alignment_message(self, session_id: str, message: str) -> dict:
        return append_alignment_message_command(
            self._alignment_context_factory().message_context(),
            session_id,
            message,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            confirmed_stages=ALIGNMENT_CONFIRMED_STAGES,
        )

    def append_alignment_message_sync(self, session_id: str, message: str) -> dict:
        context_factory = self._alignment_context_factory()
        message_context = context_factory.message_context()
        sync_message_context = message_context.__class__(
            get_session=message_context.get_session,
            transcript_context=message_context.transcript_context,
            start_session_async=lambda target_session_id: start_alignment_session_sync_lifecycle(
                context_factory.session_lifecycle_context(),
                target_session_id,
                active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            ),
            now=message_context.now,
        )
        return append_alignment_message_command(
            sync_message_context,
            session_id,
            message,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            confirmed_stages=ALIGNMENT_CONFIRMED_STAGES,
        )

    def start_alignment_session_async(self, session_id: str) -> None:
        start_alignment_session_lifecycle(
            self._alignment_context_factory().session_lifecycle_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
        )

    def cancel_alignment_session(self, session_id: str) -> dict:
        return cancel_alignment_session_lifecycle(
            self._alignment_context_factory().session_lifecycle_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            logger=logger,
        )

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        return list_alignment_events_command(
            self._alignment_context_factory().session_access_context(),
            session_id,
            after_id=after_id,
            limit=limit,
        )

    def latest_alignment_event_id(self, session_id: str) -> int:
        return latest_alignment_event_id_command(self._alignment_context_factory().session_access_context(), session_id)

    def get_alignment_workdir_context(self, workdir: Path) -> dict:
        return get_alignment_workdir_context_command(self._alignment_context_factory().loopora_context_resolver_context(), workdir)

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
            self._alignment_context_factory().loopora_context_resolver_context(),
            workdir,
            AlignmentLooporaContextResolutionRequest(
                intent=intent,
                adapter=adapter,
                context_id=context_id,
                source_option_id=source_option_id,
            ),
        )

    def get_alignment_bundle(self, session_id: str) -> dict:
        return alignment_bundle_preview(self._alignment_context_factory().bundle_preview_context(), self.get_alignment_session(session_id))

    def _alignment_context_factory(self) -> AlignmentServiceContextFactory:
        return AlignmentServiceContextFactory(self, logger)

    def sync_alignment_bundle_from_file(self, session_id: str) -> dict:
        return sync_alignment_bundle_from_file_command(
            self._alignment_context_factory().sync_context(),
            session_id,
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
        )

    def import_alignment_bundle(self, session_id: str, *, start_immediately: bool = True, execute_async: bool = True) -> dict:
        return import_alignment_bundle_command(
            self._alignment_context_factory().import_context(session_id),
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
        return create_bundle_revision_alignment_session_command(
            self._alignment_context_factory().revision_context(),
            bundle_id,
            request,
        )

    def create_run_revision_session(
        self,
        run_id: str,
        request: RevisionSessionOptions | None = None,
        **raw_request: object,
    ) -> dict:
        request = coerce_revision_session_options(request, raw_request)
        return create_run_revision_alignment_session_command(
            self._alignment_context_factory().revision_context(),
            run_id,
            request,
        )
