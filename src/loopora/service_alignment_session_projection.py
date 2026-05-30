from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_artifacts import alignment_session_root
from loopora.service_alignment_run_recovery import agent_entry_launch_projection, agent_entry_review_projection
from loopora.service_alignment_stage import alignment_session_user_task_text
from loopora.service_types import LooporaNotFoundError


class AlignmentSessionProjectionRepository(Protocol):
    def get_alignment_session(self, session_id: str) -> dict | None: ...

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]: ...

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]: ...

    def latest_alignment_event_id(self, session_id: str) -> int: ...


@dataclass(frozen=True)
class AlignmentSessionAccessContext:
    repository: AlignmentSessionProjectionRepository
    ensure_session_layout: Callable[[dict], dict]
    candidate_event: Callable[[str], dict]
    ready_event: Callable[[str], dict]
    active_statuses: set[str]
    missing_judgment_item_ids: list[str]


def get_alignment_session(context: AlignmentSessionAccessContext, session_id: str) -> dict:
    session = context.repository.get_alignment_session(session_id)
    if not session:
        raise LooporaNotFoundError(f"unknown alignment session: {session_id}")
    session = context.ensure_session_layout(session)
    normalized_session_id = str(session.get("id") or "")
    return alignment_session_detail_projection(
        session,
        active_statuses=context.active_statuses,
        candidate_event=context.candidate_event(normalized_session_id),
        ready_event=context.ready_event(normalized_session_id),
        missing_judgment_item_ids=context.missing_judgment_item_ids,
    )


def list_alignment_sessions(context: AlignmentSessionAccessContext, *, limit: int = 30) -> list[dict]:
    return [alignment_session_summary(item, active_statuses=context.active_statuses) for item in context.repository.list_alignment_sessions(limit=limit)]


def list_alignment_events(context: AlignmentSessionAccessContext, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
    get_alignment_session(context, session_id)
    return context.repository.list_alignment_events(session_id, after_id=after_id, limit=limit)


def latest_alignment_event_id(context: AlignmentSessionAccessContext, session_id: str) -> int:
    get_alignment_session(context, session_id)
    return context.repository.latest_alignment_event_id(session_id)


def decorate_alignment_session(session: dict, *, active_statuses: set[str]) -> dict:
    payload = dict(session)
    payload["artifact_dir"] = str(alignment_session_root(payload))
    payload["is_active"] = payload.get("status") in active_statuses
    payload["is_ready"] = payload.get("status") == "ready"
    payload["alignment_stage"] = str(payload.get("alignment_stage", "") or "clarifying")
    working_agreement = payload.get("working_agreement")
    if not isinstance(working_agreement, dict):
        working_agreement = {}
    payload["working_agreement"] = working_agreement
    executor_session_ref = payload.get("executor_session_ref")
    if not isinstance(executor_session_ref, dict):
        executor_session_ref = {}
    payload["executor_session_ref"] = executor_session_ref
    payload["native_resume_available"] = bool(executor_session_ref.get("session_id"))
    return payload


def alignment_session_detail_projection(
    session: dict,
    *,
    active_statuses: set[str],
    candidate_event: dict,
    ready_event: dict,
    missing_judgment_item_ids: list[str],
) -> dict:
    decorated = decorate_alignment_session(session, active_statuses=active_statuses)
    decorated["agent_entry_review"] = agent_entry_review_projection(
        decorated,
        candidate_event=candidate_event,
        task_message=alignment_session_user_task_text(decorated)[:1000],
        missing_judgment_item_ids=missing_judgment_item_ids,
    )
    decorated["agent_entry_launch"] = agent_entry_launch_projection(
        decorated,
        candidate_event=candidate_event,
        ready_event=ready_event,
    )
    return decorated


def alignment_session_summary(session: dict, *, active_statuses: set[str]) -> dict:
    decorated = decorate_alignment_session(session, active_statuses=active_statuses)
    transcript = decorated.get("transcript") or []
    first_user = ""
    last_message = ""
    for entry in transcript:
        if not isinstance(entry, dict):
            continue
        content = redact_sensitive_text(str(entry.get("content", "") or "").strip())
        if not content:
            continue
        if not first_user and entry.get("role") == "user":
            first_user = content
        last_message = content
    return {
        "id": decorated["id"],
        "status": decorated.get("status", ""),
        "workdir": decorated.get("workdir", ""),
        "executor_kind": decorated.get("executor_kind", "codex"),
        "executor_mode": decorated.get("executor_mode", "preset"),
        "alignment_stage": decorated.get("alignment_stage", "clarifying"),
        "updated_at": decorated.get("updated_at", ""),
        "created_at": decorated.get("created_at", ""),
        "linked_bundle_id": decorated.get("linked_bundle_id", ""),
        "linked_loop_id": decorated.get("linked_loop_id", ""),
        "linked_run_id": decorated.get("linked_run_id", ""),
        "message_count": len(transcript),
        "title": first_user[:96] if first_user else decorated["id"],
        "last_message": last_message[:160],
        "native_resume_available": decorated.get("native_resume_available", False),
    }
