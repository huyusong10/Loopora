from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import BundleError
from loopora.service_alignment_artifacts import alignment_repair_attempts
from loopora.service_alignment_bundle_lifecycle import (
    AlignmentBundleLifecycleContext,
    apply_alignment_bundle_write_started,
    apply_alignment_validation_failure,
    apply_alignment_validation_success,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
)
from loopora.service_alignment_execution import (
    AlignmentExecutionState,
    AlignmentSessionTransitionPlan,
    alignment_bundle_candidate_outcome,
    alignment_bundle_ready_transition_plan,
    alignment_bundle_repair_transition_plan,
)
from loopora.service_types import LooporaError
from loopora.utils import utc_now


class AlignmentBundleCandidateRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


class AlignmentBundleTextLoader(Protocol):
    def __call__(self, session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]: ...


@dataclass(frozen=True)
class AlignmentBundleCandidateContext:
    repository: AlignmentBundleCandidateRepository
    get_session: Callable[[str], dict]
    load_validated_bundle_text: AlignmentBundleTextLoader
    bundle_lifecycle_context: Callable[[], AlignmentBundleLifecycleContext]
    apply_transition_plan: Callable[[str, AlignmentSessionTransitionPlan], None]
    fail_session: Callable[[str, str], None]
    now: Callable[[], str] = utc_now


def handle_alignment_bundle_candidate(
    context: AlignmentBundleCandidateContext,
    session_id: str,
    bundle_yaml: str,
) -> AlignmentExecutionState | None:
    ok, error = write_and_validate_alignment_bundle(context, session_id, bundle_yaml)
    repair_attempts = 0
    if not ok:
        session = context.get_session(session_id)
        repair_attempts = alignment_repair_attempts(session, invalid_default=1)
    outcome = alignment_bundle_candidate_outcome(
        ok=ok,
        error=error,
        repair_attempts=repair_attempts,
        bundle_yaml=bundle_yaml,
    )
    if outcome.action == "ready":
        context.apply_transition_plan(
            session_id,
            alignment_bundle_ready_transition_plan(bundle_path=str(context.get_session(session_id)["bundle_path"])),
        )
        return None
    if outcome.action == "failed":
        context.fail_session(session_id, outcome.error)
        return None
    context.apply_transition_plan(session_id, alignment_bundle_repair_transition_plan(outcome))
    return outcome.next_state


def write_and_validate_alignment_bundle(
    context: AlignmentBundleCandidateContext,
    session_id: str,
    bundle_yaml: str,
) -> tuple[bool, str]:
    session = context.get_session(session_id)
    bundle_path = Path(session["bundle_path"])
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(bundle_yaml.rstrip() + "\n", encoding="utf-8")
    session = apply_alignment_bundle_write_started(
        context.repository,
        session_id,
        bundle_path=bundle_path,
        bundle_yaml=bundle_yaml,
    )
    semantic_issues: list[str] = []
    try:
        _bundle, normalized_yaml = context.load_validated_bundle_text(session, bundle_yaml, semantic_issues)
        bundle_path.write_text(normalized_yaml, encoding="utf-8")
    except (BundleError, LooporaError) as exc:
        error = str(exc)
        validation = alignment_bundle_validation_failure(
            bundle_path,
            error=error,
            semantic_issues=semantic_issues,
            checked_at=context.now(),
        )
        apply_alignment_validation_failure(
            context.bundle_lifecycle_context(),
            session_id,
            validation=validation,
            error=error,
        )
        return False, error
    validation = alignment_bundle_validation_success(
        bundle_path,
        checked_at=context.now(),
        normalized_yaml=normalized_yaml,
    )
    apply_alignment_validation_success(
        context.bundle_lifecycle_context(),
        session_id,
        validation=validation,
    )
    return True, ""
