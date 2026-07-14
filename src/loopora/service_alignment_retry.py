from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from loopora.service_alignment_executor_settings import (
    alignment_executor_settings_from_raw,
    normalize_alignment_executor_settings,
)
from loopora.service_alignment_failure_recovery import (
    ALIGNMENT_GENERATION_RETRY,
    ALIGNMENT_WORKER_INTERRUPTED,
    alignment_failure_recovery_projection,
)
from loopora.service_types import LooporaConflictError


class AlignmentRetryRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentGenerationRetryContext:
    repository: AlignmentRetryRepository
    get_session: Callable[[str], dict]
    start_session_async: Callable[[str], None]


def retry_alignment_generation(
    context: AlignmentGenerationRetryContext,
    session_id: str,
    raw_settings: Mapping[str, object],
) -> dict:
    session = context.get_session(session_id)
    recovery = alignment_failure_recovery_projection(session)
    if recovery.get("kind") not in {ALIGNMENT_GENERATION_RETRY, ALIGNMENT_WORKER_INTERRUPTED}:
        raise LooporaConflictError("alignment generation retry is not available")
    settings = normalize_alignment_executor_settings(
        alignment_executor_settings_from_raw(_merged_executor_settings(session, raw_settings))
    )
    context.repository.update_alignment_session(
        session_id,
        **settings,
        validation={},
        repair_attempts=0,
    )
    context.repository.append_alignment_event(
        session_id,
        "alignment_generation_retry_requested",
        {
            "status": "failed",
            "executor_kind": settings["executor_kind"],
            "executor_mode": settings["executor_mode"],
        },
    )
    context.start_session_async(session_id)
    return context.get_session(session_id)


def _merged_executor_settings(session: Mapping[str, object], raw_settings: Mapping[str, object]) -> dict[str, object]:
    fields = (
        "executor_kind",
        "executor_mode",
        "command_cli",
        "command_args_text",
        "model",
        "reasoning_effort",
    )
    return {field: raw_settings[field] if field in raw_settings else session.get(field, "") for field in fields}
