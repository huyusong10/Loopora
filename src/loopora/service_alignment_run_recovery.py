from __future__ import annotations

from collections.abc import Callable

from loopora.service_alignment_agent_entry_review import agent_entry_candidate_adapter, agent_entry_candidate_payload
from loopora.service_alignment_context import (
    alignment_context_title_from_session,
    bounded_alignment_context_options,
)
from loopora.service_alignment_run_context_choices import (
    agent_run_context_choice_payload,
    agent_run_context_next_action,
)
from loopora.service_alignment_run_context_choices import (
    agent_failed_preview_choice_repair_fields,
    agent_run_context_task_verdict,
)
from loopora.service_types import LooporaError


AGENT_RECOVERY_EVENT_LIMIT = 50
AGENT_RECOVERY_SESSION_LIMIT = 100

def agent_recovery_alignment_sessions(repository: object) -> list[dict]:
    list_sessions = getattr(repository, "list_all_alignment_sessions", None)
    if callable(list_sessions):
        return list(list_sessions())
    return list(repository.list_alignment_sessions(limit=AGENT_RECOVERY_SESSION_LIMIT))


def agent_recovery_session_events(repository: object, session_id: str) -> list[dict]:
    return list(repository.list_alignment_events(session_id, limit=AGENT_RECOVERY_EVENT_LIMIT))


def agent_recovery_session_has_candidate_yaml(repository: object, session_id: str) -> bool:
    return agent_candidate_events_include_yaml(agent_recovery_session_events(repository, session_id))


def agent_recovery_agent_entry_candidate_event(repository: object, session_id: str) -> dict:
    return latest_agent_entry_event(agent_recovery_session_events(repository, session_id), "agent_candidate_received")


def agent_recovery_agent_entry_ready_event(repository: object, session_id: str) -> dict:
    return latest_agent_entry_event(agent_recovery_session_events(repository, session_id), "agent_candidate_ready_content")


def agent_recovery_bundle_sync_failed_event(repository: object, session_id: str) -> dict:
    return latest_alignment_bundle_sync_failed_event(agent_recovery_session_events(repository, session_id))


def agent_run_context_source_entries(
    repository: object,
    *,
    root: object,
    adapter: str,
    same_workdir: Callable[[object, object], bool],
) -> list[tuple[dict, dict, str]]:
    entries: list[tuple[dict, dict, str]] = []
    for session in agent_recovery_alignment_sessions(repository):
        if not same_workdir(session.get("workdir"), root):
            continue
        candidate_event = agent_recovery_agent_entry_candidate_event(repository, str(session.get("id") or ""))
        if not candidate_event:
            continue
        payload = agent_entry_candidate_payload(candidate_event)
        event_adapter = agent_entry_candidate_adapter(session, payload)
        if adapter and event_adapter != adapter:
            continue
        entries.append((session, payload, event_adapter))
    return entries


def agent_run_context_choices(
    repository: object,
    *,
    root: object,
    adapter: str,
    same_workdir: Callable[[object, object], bool],
    get_run: Callable[[str], dict],
) -> list[dict]:
    choices: list[dict] = []
    seen: set[str] = set()
    for session, payload, event_adapter in agent_run_context_source_entries(
        repository,
        root=root,
        adapter=adapter,
        same_workdir=same_workdir,
    ):
        choice = agent_run_context_choice_from_session(
            repository,
            session,
            adapter=event_adapter,
            payload=payload,
            get_run=get_run,
        )
        option_id = str(choice.get("option_id") or "")
        if option_id and option_id not in seen:
            choices.append(choice)
            seen.add(option_id)
    return bounded_alignment_context_options(choices)


def agent_run_context_choice_from_session(
    repository: object,
    session: dict,
    *,
    adapter: str,
    get_run: Callable[[str], dict],
    payload: dict | None = None,
) -> dict:
    linked_run_id = str(session.get("linked_run_id") or "").strip()
    linked_run_status = ""
    task_verdict_status = ""
    task_verdict_summary = ""
    linked_run_found = True
    if linked_run_id:
        try:
            run = get_run(linked_run_id)
            linked_run_status = str(run.get("status") or "")
            task_verdict = agent_run_context_task_verdict(run)
            task_verdict_status = str(task_verdict.get("status") or "")
            task_verdict_summary = str(task_verdict.get("summary") or "")
        except LooporaError:
            linked_run_found = False
    next_action = agent_run_context_next_action(
        session_status=str(session.get("status") or ""),
        linked_run_id=linked_run_id,
        linked_run_status=linked_run_status,
        task_verdict_status=task_verdict_status,
        linked_run_found=linked_run_found,
    )
    choice = agent_run_context_choice_payload(
        session,
        adapter=adapter,
        payload=payload,
        title=alignment_context_title_from_session(session),
        linked_run_status=linked_run_status,
        task_verdict_status=task_verdict_status,
        task_verdict_summary=task_verdict_summary,
        next_action=next_action,
    )
    if next_action == "repair_failed_preview":
        session_id = str(session.get("id") or "").strip()
        failed_event = agent_recovery_bundle_sync_failed_event(repository, session_id)
        failed_payload = failed_event.get("payload") if isinstance(failed_event.get("payload"), dict) else {}
        choice.update(agent_failed_preview_choice_repair_fields(session, payload=payload, failed_payload=failed_payload))
    return choice


def latest_alignment_bundle_sync_failed_event(events: list[dict]) -> dict:
    failed_events = [
        event
        for event in events
        if event.get("event_type") == "alignment_bundle_sync_failed" and isinstance(event.get("payload"), dict)
    ]
    return failed_events[-1] if failed_events else {}


def latest_agent_entry_event(events: list[dict], event_type: str) -> dict:
    entry_events = [
        event
        for event in events
        if event.get("event_type") == event_type
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("candidate_origin") == "agent_entry"
    ]
    return entry_events[-1] if entry_events else {}


def agent_candidate_events_include_yaml(events: list[dict]) -> bool:
    return any(
        event.get("event_type") == "agent_candidate_received"
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("has_candidate_yaml") is True
        for event in events
    )
