from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from loopora.service_alignment_execution import AlignmentSessionTransitionPlan
from loopora.utils import utc_now


class AlignmentSessionStateRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


class AlignmentTransitionPlanApplier(Protocol):
    def __call__(self, session_id: str, plan: AlignmentSessionTransitionPlan) -> None: ...


class AlignmentSessionFailer(Protocol):
    def __call__(self, session_id: str, error: str, *, event_type: str = "alignment_failed") -> None: ...


@dataclass(frozen=True)
class AlignmentSessionStateContext:
    repository: AlignmentSessionStateRepository
    now: Callable[[], str] = utc_now


@dataclass(frozen=True)
class AlignmentSessionStateCallbacks:
    apply_transition_plan: AlignmentTransitionPlanApplier
    fail_session: AlignmentSessionFailer


def alignment_session_state_callbacks(context: AlignmentSessionStateContext) -> AlignmentSessionStateCallbacks:
    def apply_transition_plan_callback(session_id: str, plan: AlignmentSessionTransitionPlan) -> None:
        apply_alignment_session_transition_plan(context, session_id, plan)

    def fail_session_callback(session_id: str, error: str, *, event_type: str = "alignment_failed") -> None:
        fail_alignment_session(context, session_id, error, event_type=event_type)

    return AlignmentSessionStateCallbacks(
        apply_transition_plan=apply_transition_plan_callback,
        fail_session=fail_session_callback,
    )


def apply_alignment_session_transition_plan(
    context: AlignmentSessionStateContext,
    session_id: str,
    plan: AlignmentSessionTransitionPlan,
) -> None:
    update_fields = dict(plan.update_fields)
    if plan.finish_session:
        update_fields["finished_at"] = context.now()
    if plan.clear_active_child_pid:
        update_fields["clear_active_child_pid"] = True
    context.repository.update_alignment_session(session_id, **update_fields)
    context.repository.append_alignment_event(session_id, plan.event_type, plan.event_payload)


def fail_alignment_session(
    context: AlignmentSessionStateContext,
    session_id: str,
    error: str,
    *,
    event_type: str = "alignment_failed",
) -> None:
    context.repository.update_alignment_session(
        session_id,
        status="failed",
        finished_at=context.now(),
        clear_active_child_pid=True,
        error_message=error,
    )
    context.repository.append_alignment_event(
        session_id,
        event_type,
        {"status": "failed", "error": error},
    )
