from __future__ import annotations

import threading
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Protocol

from loopora.diagnostics import log_exception
from loopora.executor import ExecutionStopped
from loopora.service_alignment_execution import (
    AlignmentExecutionState,
    AlignmentSessionTransitionPlan,
    alignment_executor_output_action,
    alignment_executor_output_failure_message,
    alignment_waiting_user_transition_plan,
)


class AlignmentOrchestrationRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...


class AlignmentOrchestrationThread(Protocol):
    def is_alive(self) -> bool: ...


class AlignmentRunExecutor(Protocol):
    def __call__(
        self,
        session_id: str,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> dict: ...


class AlignmentOutputMessageProjector(Protocol):
    def __call__(self, session_id: str, session: dict, output: dict) -> tuple[str, str, list[dict], list[str] | None]: ...


class AlignmentAssistantMessageRecorder(Protocol):
    def __call__(
        self,
        session_id: str,
        session: dict,
        assistant_message: str,
        *,
        decision_options: list[dict] | None = None,
        missing_items: list[str] | None = None,
    ) -> None: ...


class AlignmentSessionFailer(Protocol):
    def __call__(self, session_id: str, error: str, *, event_type: str = "alignment_failed") -> None: ...


@dataclass(frozen=True)
class AlignmentSessionOrchestrationContext:
    repository: AlignmentOrchestrationRepository
    get_session: Callable[[str], dict]
    run_executor: AlignmentRunExecutor
    apply_output_stage: Callable[[str, dict, dict], dict]
    output_message_bundle_and_options: AlignmentOutputMessageProjector
    record_assistant_message: AlignmentAssistantMessageRecorder
    handle_bundle_candidate: Callable[[str, str], AlignmentExecutionState | None]
    apply_transition_plan: Callable[[str, AlignmentSessionTransitionPlan], None]
    fail_session: AlignmentSessionFailer
    threads: MutableMapping[str, AlignmentOrchestrationThread]
    thread_key: Callable[[str], str]
    current_thread: Callable[[], object] = threading.current_thread


def execute_alignment_session(
    context: AlignmentSessionOrchestrationContext,
    session_id: str,
    *,
    logger,
) -> None:
    key = context.thread_key(session_id)
    state = AlignmentExecutionState()
    try:
        while True:
            output = context.run_executor(
                session_id,
                mode=state.mode,
                validation_error=state.validation_error,
                invalid_yaml=state.invalid_yaml,
            )
            session = context.get_session(session_id)
            session = context.apply_output_stage(session_id, session, output)
            assistant_message, bundle_yaml, decision_options, missing_items = context.output_message_bundle_and_options(
                session_id,
                session,
                output,
            )
            if assistant_message:
                context.record_assistant_message(
                    session_id,
                    session,
                    assistant_message,
                    decision_options=decision_options,
                    missing_items=missing_items,
                )

            output_action = alignment_executor_output_action(
                output,
                assistant_message=assistant_message,
                bundle_yaml=bundle_yaml,
            )
            if output_action == "bundle":
                next_state = context.handle_bundle_candidate(session_id, bundle_yaml)
                if next_state is None:
                    return
                state = next_state
                continue

            if output_action == "waiting_user":
                context.apply_transition_plan(session_id, alignment_waiting_user_transition_plan())
                return
            message = alignment_executor_output_failure_message(assistant_message)
            context.fail_session(session_id, message)
            return
    except ExecutionStopped:
        context.fail_session(session_id, "Cancelled by user.", event_type="alignment_cancelled")
    except Exception as exc:  # noqa: BLE001 - alignment worker crash boundary must persist session failure.
        log_exception(
            logger,
            "service.alignment.failed",
            "Alignment session failed",
            error=exc,
            session_id=session_id,
        )
        context.fail_session(session_id, str(exc) or type(exc).__name__)
    finally:
        context.repository.update_alignment_session(session_id, clear_active_child_pid=True)
        thread = context.threads.get(key)
        if (thread is context.current_thread()) or (thread is not None and not thread.is_alive()):
            context.threads.pop(key, None)
