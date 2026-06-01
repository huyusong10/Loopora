from __future__ import annotations

import logging

from loopora.service_alignment_artifacts import ensure_alignment_artifact_dirs
from loopora.service_alignment_context_protocols import AlignmentFactoryService
from loopora.service_alignment_diagnostics import append_alignment_diagnostic_event, append_alignment_local_diagnostic_event
from loopora.service_alignment_legacy import AlignmentLegacyLayoutContext, ensure_alignment_session_layout


def ensure_alignment_session_layout_from_service(
    service: AlignmentFactoryService,
    logger: logging.Logger,
    session: dict,
) -> dict:
    return ensure_alignment_session_layout(
        AlignmentLegacyLayoutContext(
            repository=service.repository,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            append_diagnostic_event=lambda session_id, event_type, payload: append_alignment_service_diagnostic_event(
                service,
                logger,
                session_id,
                event_type,
                payload,
            ),
        ),
        session,
    )


def append_alignment_service_diagnostic_event(
    service: AlignmentFactoryService,
    logger: logging.Logger,
    session_id: str,
    event_type: str,
    payload: dict,
) -> dict:
    return append_alignment_diagnostic_event(service.repository, logger, session_id, event_type, payload)


def append_alignment_service_local_diagnostic_event(
    logger: logging.Logger,
    session: dict,
    event_type: str,
    payload: dict,
) -> None:
    append_alignment_local_diagnostic_event(ensure_alignment_artifact_dirs, logger, session, event_type, payload)
