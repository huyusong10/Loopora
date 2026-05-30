from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from loopora.service_alignment_stage import alignment_user_message_stage_plan
from loopora.service_alignment_transcript import (
    AlignmentTranscriptContext,
    AlignmentUserMessageEffect,
    apply_alignment_user_message,
)
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.utils import utc_now


@dataclass(frozen=True)
class AlignmentMessageContext:
    get_session: Callable[[str], dict]
    transcript_context: Callable[[], AlignmentTranscriptContext]
    start_session_async: Callable[[str], None]
    now: Callable[[], str] = utc_now


def append_alignment_message(
    context: AlignmentMessageContext,
    session_id: str,
    message: str,
    *,
    active_statuses: set[str],
    confirmed_stages: set[str],
) -> dict:
    normalized = str(message or "").strip()
    if not normalized:
        raise LooporaError("message is required")
    session = context.get_session(session_id)
    if session["status"] in active_statuses:
        raise LooporaConflictError("alignment session is already running")
    message_created_at = context.now()
    stage_plan = alignment_user_message_stage_plan(
        session,
        normalized,
        captured_at=message_created_at,
        confirmed_stages=confirmed_stages,
    )
    apply_alignment_user_message(
        context.transcript_context(),
        session_id,
        AlignmentUserMessageEffect(
            session=session,
            message=normalized,
            created_at=message_created_at,
            update_fields=stage_plan.update_fields,
            stage_event_type=stage_plan.event_type,
            stage_event_payload=stage_plan.event_payload,
        ),
    )
    context.start_session_async(session_id)
    return context.get_session(session_id)
