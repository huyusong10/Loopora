from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from loopora.service_alignment_artifacts import (
    alignment_assistant_message_record,
    alignment_user_message_record,
    write_alignment_transcript_log,
)
from loopora.utils import utc_now


class AlignmentTranscriptRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentTranscriptContext:
    repository: AlignmentTranscriptRepository
    get_session: Callable[[str], dict]


class AlignmentNoticeAppender(Protocol):
    def __call__(self, session_id: str, content: str) -> dict: ...


@dataclass(frozen=True)
class AlignmentUserMessageEffect:
    session: dict
    message: str
    created_at: str
    update_fields: dict
    stage_event_type: str = ""
    stage_event_payload: dict | None = None


@dataclass(frozen=True)
class AlignmentAssistantMessageEffect:
    session: dict
    message: str
    created_at: str
    decision_options: list[dict] | None = None
    missing_items: list[str] | None = None


def alignment_notice_appender(
    context: AlignmentTranscriptContext,
    *,
    now: Callable[[], str] = utc_now,
) -> AlignmentNoticeAppender:
    def append_notice(session_id: str, content: str) -> dict:
        return append_alignment_notice_message(
            context,
            session_id,
            content=content,
            created_at=now(),
        )

    return append_notice


def apply_alignment_user_message(
    context: AlignmentTranscriptContext,
    session_id: str,
    effect: AlignmentUserMessageEffect,
) -> dict:
    transcript = list(effect.session.get("transcript") or [])
    record = alignment_user_message_record(effect.message, created_at=effect.created_at)
    transcript.append(record.entry)
    update_fields = {
        "transcript": transcript,
        "error_message": "",
        "stop_requested": False,
        "repair_attempts": 0,
        "finished_at": None,
    }
    update_fields.update(effect.update_fields)
    context.repository.update_alignment_session(session_id, **update_fields)
    context.repository.append_alignment_event(session_id, "alignment_user_message", record.event_payload)
    if effect.stage_event_type:
        context.repository.append_alignment_event(
            session_id,
            effect.stage_event_type,
            effect.stage_event_payload or {},
        )
    updated = context.get_session(session_id)
    write_alignment_transcript_log(updated)
    return updated


def record_alignment_assistant_message(
    context: AlignmentTranscriptContext,
    session_id: str,
    effect: AlignmentAssistantMessageEffect,
) -> None:
    transcript = list(effect.session.get("transcript") or [])
    record = alignment_assistant_message_record(
        effect.message,
        created_at=effect.created_at,
        decision_options=effect.decision_options,
        missing_items=effect.missing_items,
    )
    transcript.append(record.entry)
    context.repository.update_alignment_session(session_id, transcript=transcript)
    write_alignment_transcript_log(context.get_session(session_id))
    context.repository.append_alignment_event(session_id, "alignment_message", record.event_payload)


def append_alignment_notice_message(
    context: AlignmentTranscriptContext,
    session_id: str,
    *,
    content: str,
    created_at: str,
) -> dict:
    session = context.get_session(session_id)
    transcript = list(session.get("transcript") or [])
    transcript.append({"role": "assistant", "content": content, "created_at": created_at})
    context.repository.update_alignment_session(session_id, transcript=transcript)
    updated = context.get_session(session_id)
    write_alignment_transcript_log(updated)
    return updated
