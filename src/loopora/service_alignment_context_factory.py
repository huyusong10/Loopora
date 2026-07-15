from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import os
from pathlib import Path

from loopora.service_alignment_artifacts import ensure_alignment_artifact_dirs, write_alignment_validation_log
from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext
from loopora.service_alignment_bundle_preview import AlignmentBundlePreviewContext
from loopora.service_alignment_session_layout_context import AlignmentFactoryService
from loopora.service_alignment_source_seed import redact_alignment_source_value
from loopora.service_alignment_delete import AlignmentDeleteContext
from loopora.service_alignment_import import AlignmentImportContext
from loopora.service_alignment_invocation import AlignmentExecutorRunContext
from loopora.service_alignment_orchestration import AlignmentSessionOrchestrationContext, execute_alignment_session
from loopora.service_alignment_output_stage import (
    AlignmentOutputStageContext,
)
from loopora.service_alignment_requests import (
    ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
)
from loopora.service_alignment_revision import AlignmentRevisionContext
from loopora.service_alignment_run_recovery import (
    agent_recovery_agent_entry_candidate_event,
    agent_recovery_agent_entry_ready_event,
)
from loopora.service_alignment_session_creation import AlignmentSessionCreationContext, alignment_session_dir
from loopora.service_alignment_session_lifecycle import AlignmentSessionLifecycleContext, alignment_thread_key
from loopora.service_alignment_session_layout_context import (
    append_alignment_service_diagnostic_event,
    append_alignment_service_local_diagnostic_event,
    ensure_alignment_session_layout_from_service,
)
from loopora.service_alignment_session_projection import AlignmentSessionAccessContext, decorate_alignment_session
from loopora.service_alignment_sync import AlignmentSyncContext
from loopora.service_alignment_transcript import (
    AlignmentTranscriptContext,
    alignment_notice_appender,
)
from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolverContext,
    AlignmentWorkdirContextResolverContext,
)




from loopora.service_alignment_workdir_context import (
    alignment_workdir_context_payload,
    resolve_plan_context_from_workdir_context,
)

from loopora.service_alignment_workdir_snapshot import alignment_same_workdir

from loopora.service_alignment_artifacts import (
    alignment_next_invocation_dir,
    alignment_repair_attempts,
)


from loopora.service_alignment_invocation import (
    AlignmentExecutorInvocationConfig,
)

from loopora.service_alignment_prompting import (
    AlignmentPromptBuildContext,
    build_alignment_prompt as build_alignment_prompt_command,
)

from loopora.service_alignment_requests import ALIGNMENT_RESPONSE_SCHEMA

from typing import Protocol

from loopora.alignment_readiness_rules import ALIGNMENT_READINESS_EVIDENCE_KEYS



from loopora.service_alignment_execution import AlignmentExecutionState

from loopora.service_alignment_invocation import (
    run_alignment_executor as run_alignment_executor_command,
)



from loopora.service_alignment_output_stage import (
    AlignmentOutputStageRequest,
    apply_alignment_output_stage as apply_alignment_output_stage_command,
)

from loopora.service_alignment_requests import ALIGNMENT_MISSING_ITEM_IDS, ALIGNMENT_READINESS_KEYS




from loopora.service_alignment_transcript import (
    AlignmentAssistantMessageEffect,
    record_alignment_assistant_message,
)

from loopora.utils import utc_now





from loopora.bundles import BundleError


from loopora.service_alignment_bundle_lifecycle import (
    apply_alignment_bundle_write_started,
    apply_alignment_validation_failure,
    apply_alignment_validation_success,
    alignment_bundle_validation_failure,
    alignment_bundle_validation_success,
)

from loopora.service_alignment_execution import (
    AlignmentSessionTransitionPlan,
    alignment_bundle_candidate_outcome,
    alignment_bundle_ready_transition_plan,
    alignment_bundle_repair_transition_plan,
)

from loopora.service_types import LooporaError




from loopora.service_alignment_decision_options import (
    default_alignment_decision_options,
    normalize_alignment_missing_items,
    visible_alignment_decision_options,
)

from loopora.service_alignment_language import (
    alignment_generation_display_language,
    alignment_generation_prefers_chinese,
    alignment_prefers_chinese,
)

from loopora.service_alignment_output_stage import alignment_output_bundle_stage_check

from loopora.service_alignment_stage_messages import alignment_output_message_plan





from loopora.agent_adapters import read_agent_binding

from loopora.service_alignment_run_context_choices import (
    agent_run_context_choice_summary,
)

from loopora.service_alignment_run_context_choices import (
    agent_exact_binding_recovery_action,
    agent_redacted_context_binding,
)

from loopora.service_alignment_run_recovery import (
    agent_run_context_choice_from_session,
    agent_run_context_choices,
)








from loopora.bundles import load_bundle_text, read_bundle_file_text

from loopora.service_alignment_context import alignment_context_option_by_id, alignment_source_option_seed_kind

from loopora.service_alignment_run_source_projection import (
    alignment_run_artifact_paths,
    alignment_run_coverage_summary,
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
)

from loopora.service_alignment_source_seed import (
    alignment_bundle_source_seed,
    alignment_loop_bundle_id,
    alignment_loop_source_seed,
    alignment_revision_seed_bundle,
    alignment_run_source_seed,
    alignment_session_source_seed,
    alignment_spec_file_source_seed,
)

from loopora.service_types import LooporaConflictError




from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)

from loopora.bundles import (
    bundle_to_yaml,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
)

from loopora.service_alignment_execution import alignment_bundle_executor_settings_issues

from loopora.service_alignment_language import (
    alignment_bundle_language_issues,
)

from loopora.service_alignment_context import alignment_assert_bundle_workdir

from loopora.service_alignment_stage import (
    alignment_bundle_workdir_fact_issues,
    alignment_improvement_bundle_issues,
)

from loopora.service_alignment_traceability_projection import alignment_session_user_task_text

from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot

from loopora.service_bundle_control_summary import build_bundle_control_summary




from loopora.service_alignment_agreement_stage import alignment_user_message_stage_plan

from loopora.service_alignment_transcript import (
    AlignmentUserMessageEffect,
    apply_alignment_user_message,
    append_alignment_notice_message,
)



ALIGNMENT_ACTIVE_STATUSES = {"running", "validating", "repairing"}

ALIGNMENT_CONFIRMED_STAGES = {"confirmed", "compiling", "ready_review"}

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
    if stage_plan.assistant_message:
        append_alignment_notice_message(
            context.transcript_context(),
            session_id,
            content=stage_plan.assistant_message,
            created_at=context.now(),
        )
    if stage_plan.start_session:
        context.start_session_async(session_id)
    return context.get_session(session_id)

@dataclass(frozen=True)
class AlignmentBundleTextValidationContext:
    include_agent_candidate_loop_fit_contradiction: bool = False
    include_agent_candidate_contract_issues: bool = False

def extend_unique_alignment_issues(issues: list[str], additions: list[str]) -> None:
    for issue in additions:
        if issue not in issues:
            issues.append(issue)

def alignment_validated_bundle_text_loader(
    context: AlignmentBundleTextValidationContext,
) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
    def load_bundle(session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        return load_validated_alignment_bundle_text(
            session,
            bundle_yaml,
            semantic_issues,
            context=context,
        )

    return load_bundle

def alignment_bundle_validation_issues(
    session: dict,
    bundle: dict,
    *,
    context: AlignmentBundleTextValidationContext,
) -> list[str]:
    issue_sources = (
        lint_alignment_bundle_semantics(bundle),
        alignment_bundle_executor_settings_issues(session, bundle),
        alignment_bundle_language_issues(
            bundle,
            prefers_chinese=alignment_generation_prefers_chinese(session),
            display_language=alignment_generation_display_language(session),
        ),
        alignment_bundle_workdir_fact_issues(
            bundle,
            workdir_snapshot=alignment_workdir_snapshot(Path(session["workdir"])),
        ),
        alignment_improvement_bundle_issues(session.get("working_agreement"), bundle),
        alignment_bundle_agreement_traceability_issues(session, bundle),
        alignment_bundle_control_summary_issues(bundle),
        alignment_agent_candidate_traceability_issues(
            alignment_session_user_task_text(session),
            bundle,
            include_loop_fit_contradiction=context.include_agent_candidate_loop_fit_contradiction,
            include_candidate_contract_issues=context.include_agent_candidate_contract_issues,
        ),
    )
    issues: list[str] = []
    for source_issues in issue_sources:
        extend_unique_alignment_issues(issues, source_issues)
    return issues

def alignment_bundle_control_summary_issues(bundle: dict) -> list[str]:
    summary = build_bundle_control_summary(bundle)
    issues: list[str] = []
    for diagnostic in list(summary.get("diagnostics") or []):
        if not isinstance(diagnostic, dict):
            continue
        if str(diagnostic.get("severity") or "") == "info":
            continue
        if str(diagnostic.get("code") or "") != "traceability_missing":
            continue
        missing = [
            str(item).strip()
            for item in list(dict(diagnostic.get("details") or {}).get("missing") or [])
            if str(item).strip()
        ]
        if not missing:
            continue
        issues.append("bundle control summary missing traceability: " + ", ".join(missing))
    return issues

def load_validated_alignment_bundle_text(
    session: dict,
    bundle_yaml: str,
    semantic_issues: list[str],
    *,
    context: AlignmentBundleTextValidationContext | None = None,
) -> tuple[dict, str]:
    context = context or AlignmentBundleTextValidationContext()
    semantic_issues.extend(lint_alignment_bundle_generation_text(bundle_yaml))
    if semantic_issues:
        raise LooporaError("bundle semantic lint failed: " + "; ".join(semantic_issues))

    bundle = load_bundle_text(bundle_yaml)
    alignment_assert_bundle_workdir(bundle, expected_workdir=Path(session["workdir"]))
    extend_unique_alignment_issues(
        semantic_issues,
        alignment_bundle_validation_issues(
            session,
            bundle,
            context=context,
        ),
    )
    if semantic_issues:
        raise LooporaError("bundle semantic lint failed: " + "; ".join(semantic_issues))

    return bundle, bundle_to_yaml(bundle)

def resolve_alignment_source_option_seed(service: object, workdir: Path, source_option_id: str) -> dict:
    option_id = str(source_option_id or "").strip()
    if not option_id or option_id == "regenerate":
        return {}
    context = service.get_alignment_workdir_context(workdir)
    option = alignment_context_option_by_id(context["options"], option_id)
    if not option:
        raise LooporaError("selected workdir context is no longer available")
    if option.get("action") == "continue_session":
        raise LooporaConflictError("continue_session options must restore the existing session instead of creating a new one")
    return alignment_source_seed_from_option(service, option)

def alignment_source_seed_from_option(service: object, option: dict) -> dict:
    seed_kind = alignment_source_option_seed_kind(option)
    if seed_kind == "bundle":
        return alignment_source_seed_from_bundle_option(service, option)
    if seed_kind == "run":
        return alignment_source_seed_from_run_option(service, option)
    if seed_kind == "loop":
        return alignment_source_seed_from_loop_option(service, option)
    if seed_kind == "alignment_session":
        return alignment_source_seed_from_alignment_session_option(service, option)
    if seed_kind == "spec_file":
        return alignment_spec_file_source_seed(option)
    raise LooporaError(f"unsupported workdir context source: {seed_kind}")

def alignment_source_seed_from_bundle_option(service: object, option: dict) -> dict:
    bundle_id = str(option.get("source_bundle_id") or "").strip()
    source_bundle = service.export_bundle(bundle_id)
    return alignment_bundle_source_seed(
        option,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )

def alignment_source_seed_from_run_option(service: object, option: dict) -> dict:
    run_id = str(option.get("source_run_id") or "").strip()
    run = service.get_run(run_id)
    loop = service.get_loop(run["loop_id"])
    source_bundle_id, source_bundle = alignment_run_source_bundle(
        service,
        run,
        loop,
        fallback_description="Derived as the improvement base for a run selected from workdir context.",
    )
    return alignment_run_source_seed(
        option,
        run,
        source_bundle,
        source_bundle_id=source_bundle_id,
        artifact_paths=alignment_run_artifact_paths(run),
        judgment_contract=alignment_run_judgment_contract(run),
        coverage_summary=alignment_run_coverage_summary(run),
        evidence_summary=alignment_run_evidence_summary(run),
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )

def alignment_run_source_bundle(service: object, run: dict, loop: dict, *, fallback_description: str) -> tuple[str, dict]:
    source_bundle_id = alignment_loop_bundle_id(loop)
    if source_bundle_id:
        return source_bundle_id, service.export_bundle(source_bundle_id)
    source_bundle = service.derive_bundle_from_loop(
        run["loop_id"],
        name=str(loop.get("name") or "Run improvement base"),
        description=fallback_description,
        collaboration_summary="Improvement base derived from the current loop.",
    )
    return "", source_bundle

def alignment_source_seed_from_loop_option(service: object, option: dict) -> dict:
    loop_id = str(option.get("source_loop_id") or "").strip()
    loop = service.get_loop(loop_id)
    source_bundle = service.derive_bundle_from_loop(
        loop_id,
        name=str(loop.get("name") or "Loop improvement base"),
        description="Derived as the improvement base for a Loop selected from workdir context.",
        collaboration_summary="Improvement base derived from the current loop.",
    )
    return alignment_loop_source_seed(
        option,
        loop,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )

def alignment_source_seed_from_alignment_session_option(service: object, option: dict) -> dict:
    source_session_id = str(option.get("source_alignment_session_id") or "").strip()
    bundle_path = Path(str(option.get("bundle_path") or ""))
    try:
        source_session = service.get_alignment_session(source_session_id)
    except LooporaError:
        source_session = {}
    source_bundle = load_bundle_text(read_bundle_file_text(bundle_path))
    return alignment_session_source_seed(
        option,
        source_session,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )

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

class AlignmentAgentBindingReader(Protocol):
    def __call__(self, adapter: str, workdir: Path, *, context_id: str = "") -> dict: ...

@dataclass(frozen=True)
class AlignmentRunContextResolverContext:
    repository: object
    get_alignment_session: Callable[[str], dict]
    get_run: Callable[[str], dict]
    same_workdir: Callable[[object, object], bool]
    read_binding: AlignmentAgentBindingReader = read_agent_binding

def resolve_alignment_run_context(
    context: AlignmentRunContextResolverContext,
    root: Path,
    *,
    adapter: str,
    context_id: str,
) -> dict:
    normalized_adapter = str(adapter or "").strip()
    base = alignment_run_context_base(root, adapter=normalized_adapter, context_id=context_id)
    if normalized_adapter:
        try:
            binding = context.read_binding(normalized_adapter, root, context_id=str(context_id or "").strip())
        except LooporaError as exc:
            return {
                **base,
                "action": "repair_context_card",
                "confidence": "damaged_context_card",
                "binding_error": str(exc),
                "context_card_error": str(exc),
                "message": "Agent context card is unreadable; repair it or choose a recoverable context before /loopora-run starts.",
            }
        if binding:
            return resolve_alignment_run_context_from_exact_binding(context, root, base=base, binding=binding)
    choices = agent_run_context_choices(
        context.repository,
        root=root,
        adapter=normalized_adapter,
        same_workdir=context.same_workdir,
        get_run=context.get_run,
    )
    if choices:
        return {
            **base,
            "action": "choose_recoverable_context",
            "confidence": "single_recoverable" if len(choices) == 1 else "ambiguous",
            "requires_user_choice": True,
            **agent_run_context_choice_summary(choices),
            "choices": choices,
            "message": "Choose a recoverable Loopora run context before /loopora-run starts.",
        }
    return {
        **base,
        "action": "plan_first",
        "confidence": "no_context_card",
        "message": "No Loopora run context is bound to this Agent session/workdir; run /loopora-plan first.",
    }

def alignment_run_context_base(root: Path, *, adapter: str, context_id: str) -> dict:
    return {
        "schema_version": 1,
        "intent": "run",
        "workdir": str(root),
        "adapter": str(adapter or "").strip(),
        "context_id": str(context_id or "").strip(),
        "requires_user_choice": False,
        "choices": [],
    }

def resolve_alignment_run_context_from_exact_binding(
    context: AlignmentRunContextResolverContext,
    root: Path,
    *,
    base: dict,
    binding: dict,
) -> dict:
    session_id = str(binding.get("alignment_session_id") or "").strip()
    if not session_id:
        return {
            **base,
            "action": "blocked",
            "confidence": "stale_context_card",
            "binding": agent_redacted_context_binding(binding),
            "message": "Agent context card exists but does not reference a Loop preview; run /loopora-plan again.",
        }
    try:
        session = context.get_alignment_session(session_id)
    except LooporaError:
        return {
            **base,
            "action": "blocked",
            "confidence": "stale_context_card",
            "binding": agent_redacted_context_binding(binding),
            "alignment_session_id": session_id,
            "message": "Agent context card references a missing Loop preview; run /loopora-plan again.",
        }
    if not context.same_workdir(binding.get("workdir") or session.get("workdir"), root):
        return {
            **base,
            "action": "blocked",
            "confidence": "workdir_mismatch",
            "binding": agent_redacted_context_binding(binding),
            "alignment_session_id": session_id,
            "message": "Agent context card belongs to a different workdir; run /loopora-plan again.",
        }
    choice = agent_run_context_choice_from_session(
        context.repository,
        session,
        adapter=str(base.get("adapter") or ""),
        get_run=context.get_run,
    )
    return {
        **base,
        "action": agent_exact_binding_recovery_action(choice),
        "confidence": "exact_context_card",
        "alignment_session_id": session_id,
        "binding": agent_redacted_context_binding(binding),
        "choice": choice,
        "message": "Exact Agent context card found.",
    }

class AlignmentOutputMessageRepository(Protocol):
    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...

@dataclass(frozen=True)
class AlignmentOutputMessageContext:
    repository: AlignmentOutputMessageRepository

@dataclass(frozen=True)
class AlignmentOutputMessageRequest:
    session_id: str
    session: dict
    output: dict
    confirmed_stages: set[str]
    missing_item_ids: set[str]
    readiness_keys: list[str]
    readiness_evidence_keys: list[str]

@dataclass(frozen=True)
class AlignmentOutputMessageResult:
    assistant_message: str
    bundle_yaml: str
    decision_options: list[dict]
    missing_items: list[str] | None

def alignment_output_message_bundle_and_options(
    context: AlignmentOutputMessageContext,
    request: AlignmentOutputMessageRequest,
) -> AlignmentOutputMessageResult:
    output = request.output
    session = request.session
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    missing_items = normalize_alignment_missing_items(
        output.get("alignment_missing_items"),
        allowed_item_ids=request.missing_item_ids,
    )
    stage_check = (
        alignment_output_bundle_stage_check(
            session,
            output,
            confirmed_stages=request.confirmed_stages,
            readiness_keys=request.readiness_keys,
            readiness_evidence_keys=request.readiness_evidence_keys,
        )
        if bundle_yaml
        else None
    )
    message_plan = alignment_output_message_plan(
        output,
        stage_error=stage_check.error if stage_check else "",
        stage_missing_items=stage_check.missing_items if stage_check else [],
        missing_items=missing_items,
        prefers_chinese=alignment_generation_prefers_chinese(session),
        display_language=alignment_generation_display_language(session),
    )
    if message_plan.force_needs_user_input:
        output["needs_user_input"] = True
    if message_plan.event_type:
        context.repository.append_alignment_event(
            request.session_id,
            message_plan.event_type,
            message_plan.event_payload or {},
        )
    if message_plan.use_default_decision_options:
        output["decision_options"] = default_alignment_decision_options(
            prefers_chinese=alignment_prefers_chinese(session),
            display_language=alignment_generation_display_language(session),
        )
    decision_options = visible_alignment_decision_options(
        output,
        has_bundle=message_plan.has_bundle_for_options,
        prefers_chinese=alignment_prefers_chinese(session),
        display_language=alignment_generation_display_language(session),
    )
    return AlignmentOutputMessageResult(
        assistant_message=message_plan.assistant_message,
        bundle_yaml=message_plan.bundle_yaml,
        decision_options=decision_options,
        missing_items=message_plan.missing_items,
    )

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

class AlignmentOrchestrationContextProvider(Protocol):
    def executor_run_context(self) -> AlignmentExecutorRunContext: ...

    def output_stage_context(self) -> AlignmentOutputStageContext: ...

    def output_message_context(self) -> AlignmentOutputMessageContext: ...

    def bundle_candidate_context(self) -> AlignmentBundleCandidateContext: ...

    def transcript_context(self) -> AlignmentTranscriptContext: ...

    def session_state_context(self) -> AlignmentSessionStateContext: ...

def alignment_session_orchestration_context(
    service: AlignmentFactoryService,
    provider: AlignmentOrchestrationContextProvider,
) -> AlignmentSessionOrchestrationContext:
    state_callbacks = alignment_session_state_callbacks(provider.session_state_context())

    def run_executor(
        session_id: str,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> dict:
        return run_alignment_executor_command(
            provider.executor_run_context(),
            session_id,
            mode=mode,
            validation_error=validation_error,
            invalid_yaml=invalid_yaml,
        )

    def apply_output_stage(session_id: str, session: dict, output: dict) -> dict:
        return apply_alignment_output_stage_command(
            provider.output_stage_context(),
            AlignmentOutputStageRequest(
                session_id=session_id,
                session=session,
                output=output,
                readiness_keys=ALIGNMENT_READINESS_KEYS,
                readiness_evidence_keys=list(ALIGNMENT_READINESS_EVIDENCE_KEYS),
            ),
        )

    def handle_bundle_candidate_callback(session_id: str, bundle_yaml: str) -> AlignmentExecutionState | None:
        return handle_alignment_bundle_candidate(provider.bundle_candidate_context(), session_id, bundle_yaml)

    def record_assistant_message_callback(
        session_id: str,
        session: dict,
        assistant_message: str,
        *,
        decision_options: list[dict] | None = None,
        missing_items: list[str] | None = None,
    ) -> None:
        record_alignment_assistant_message(
            provider.transcript_context(),
            session_id,
            AlignmentAssistantMessageEffect(
                session=session,
                message=assistant_message,
                created_at=utc_now(),
                decision_options=decision_options,
                missing_items=missing_items,
            ),
        )

    def output_message_bundle_and_options(
        session_id: str,
        session: dict,
        output: dict,
    ) -> tuple[str, str, list[dict], list[str] | None]:
        result = alignment_output_message_bundle_and_options(
            provider.output_message_context(),
            AlignmentOutputMessageRequest(
                session_id=session_id,
                session=session,
                output=output,
                confirmed_stages=ALIGNMENT_CONFIRMED_STAGES,
                missing_item_ids=ALIGNMENT_MISSING_ITEM_IDS,
                readiness_keys=ALIGNMENT_READINESS_KEYS,
                readiness_evidence_keys=list(ALIGNMENT_READINESS_EVIDENCE_KEYS),
            ),
        )
        return result.assistant_message, result.bundle_yaml, result.decision_options, result.missing_items

    return AlignmentSessionOrchestrationContext(
        repository=service.repository,
        get_session=service.get_alignment_session,
        run_executor=run_executor,
        apply_output_stage=apply_output_stage,
        output_message_bundle_and_options=output_message_bundle_and_options,
        record_assistant_message=record_assistant_message_callback,
        handle_bundle_candidate=handle_bundle_candidate_callback,
        apply_transition_plan=state_callbacks.apply_transition_plan,
        fail_session=state_callbacks.fail_session,
        threads=service._threads,
        thread_key=alignment_thread_key,
    )

def alignment_executor_run_context(service: AlignmentFactoryService) -> AlignmentExecutorRunContext:
    def build_prompt(
        session: dict,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> str:
        return build_alignment_prompt_command(
            AlignmentPromptBuildContext(),
            session,
            mode=mode,
            validation_error=validation_error,
            invalid_yaml=invalid_yaml,
        )

    return AlignmentExecutorRunContext(
        repository=service.repository,
        get_session=service.get_alignment_session,
        config=AlignmentExecutorInvocationConfig(
            output_schema=ALIGNMENT_RESPONSE_SCHEMA,
            idle_timeout_seconds=service.settings.role_idle_timeout_seconds,
            executor_factory=service.executor_factory,
            build_prompt=build_prompt,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            next_invocation_dir=alignment_next_invocation_dir,
            repair_attempts=alignment_repair_attempts,
        ),
    )

def alignment_run_context_resolver_context(service: AlignmentFactoryService) -> AlignmentRunContextResolverContext:
    return AlignmentRunContextResolverContext(
        repository=service.repository,
        get_alignment_session=service.get_alignment_session,
        get_run=service.get_run,
        same_workdir=alignment_same_workdir,
    )

def alignment_workdir_context_resolver_context(service: AlignmentFactoryService) -> AlignmentWorkdirContextResolverContext:
    return AlignmentWorkdirContextResolverContext(
        repository=service.repository,
        list_loops=service.list_loops,
        get_run=service.get_run,
    )

def alignment_loopora_context_resolver_context(service: AlignmentFactoryService) -> AlignmentLooporaContextResolverContext:
    def workdir_context_payload(root: Path) -> dict:
        return alignment_workdir_context_payload(alignment_workdir_context_resolver_context(service), root)

    def resolve_plan_context(context: dict, *, source_option_id: str = "") -> dict:
        return resolve_plan_context_from_workdir_context(context, source_option_id=source_option_id)

    def resolve_run_context(root: Path, *, adapter: str, context_id: str) -> dict:
        return resolve_alignment_run_context(
            alignment_run_context_resolver_context(service),
            root=root,
            adapter=adapter,
            context_id=context_id,
        )

    return AlignmentLooporaContextResolverContext(
        workdir_context_payload=workdir_context_payload,
        resolve_plan_context=resolve_plan_context,
        resolve_run_context=resolve_run_context,
    )

build_alignment_loopora_context_resolver_context = alignment_loopora_context_resolver_context
build_alignment_run_context_resolver_context = alignment_run_context_resolver_context
build_alignment_workdir_context_resolver_context = alignment_workdir_context_resolver_context


@dataclass(frozen=True, slots=True)
class AlignmentServiceContextFactory:
    service: AlignmentFactoryService
    logger: logging.Logger

    def ensure_session_layout(self, session: dict) -> dict:
        return ensure_alignment_session_layout_from_service(self.service, self.logger, session)

    def append_diagnostic_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        return append_alignment_service_diagnostic_event(self.service, self.logger, session_id, event_type, payload)

    def append_local_diagnostic_event(self, session: dict, event_type: str, payload: dict) -> None:
        append_alignment_service_local_diagnostic_event(self.logger, session, event_type, payload)

    def bundle_lifecycle_context(self) -> AlignmentBundleLifecycleContext:
        service = self.service
        return AlignmentBundleLifecycleContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            write_validation_log=write_alignment_validation_log,
        )

    def bundle_preview_context(self) -> AlignmentBundlePreviewContext:
        service = self.service
        return AlignmentBundlePreviewContext(
            build_preview=service._bundle_preview_payload,
            load_validated_bundle_text=self.bundle_text_loader(),
        )

    def bundle_candidate_context(self) -> AlignmentBundleCandidateContext:
        service = self.service
        state_callbacks = alignment_session_state_callbacks(self.session_state_context())
        return AlignmentBundleCandidateContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            load_validated_bundle_text=self.bundle_text_loader(),
            bundle_lifecycle_context=self.bundle_lifecycle_context,
            apply_transition_plan=state_callbacks.apply_transition_plan,
            fail_session=state_callbacks.fail_session,
        )

    def session_state_context(self) -> AlignmentSessionStateContext:
        return AlignmentSessionStateContext(repository=self.service.repository)

    def session_access_context(self) -> AlignmentSessionAccessContext:
        service = self.service
        return AlignmentSessionAccessContext(
            repository=service.repository,
            ensure_session_layout=self.ensure_session_layout,
            candidate_event=lambda session_id: agent_recovery_agent_entry_candidate_event(service.repository, session_id),
            ready_event=lambda session_id: agent_recovery_agent_entry_ready_event(service.repository, session_id),
            active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            missing_judgment_item_ids=ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
        )

    def output_stage_context(self) -> AlignmentOutputStageContext:
        service = self.service
        return AlignmentOutputStageContext(
            repository=service.repository,
            decorate_session=lambda session: decorate_alignment_session(
                session,
                active_statuses=ALIGNMENT_ACTIVE_STATUSES,
            ),
        )

    def output_message_context(self) -> AlignmentOutputMessageContext:
        return AlignmentOutputMessageContext(repository=self.service.repository)

    def executor_run_context(self) -> AlignmentExecutorRunContext:
        return alignment_executor_run_context(self.service)

    def session_creation_context(self) -> AlignmentSessionCreationContext:
        service = self.service
        return AlignmentSessionCreationContext(
            repository=service.repository,
            resolve_source_seed=lambda workdir, source_option_id: resolve_alignment_source_option_seed(
                service,
                workdir,
                source_option_id,
            ),
            session_dir=alignment_session_dir,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            get_session=service.get_alignment_session,
            start_session_async=service.start_alignment_session_async,
        )

    def revision_context(self) -> AlignmentRevisionContext:
        service = self.service
        return AlignmentRevisionContext(
            repository=service.repository,
            create_session=service.create_alignment_session,
            get_session=service.get_alignment_session,
            export_bundle=service.export_bundle,
            get_run=service.get_run,
            get_loop=service.get_loop,
            run_source_bundle=lambda run, loop: alignment_run_source_bundle(
                service,
                run,
                loop,
                fallback_description="Derived as the improvement base for a run without an imported bundle.",
            ),
            start_session_async=service.start_alignment_session_async,
            redact_source_value=redact_alignment_source_value,
        )

    def import_context(self, session_id: str) -> AlignmentImportContext:
        service = self.service
        return AlignmentImportContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            has_agent_entry_candidate=lambda candidate_session_id: bool(
                agent_recovery_agent_entry_candidate_event(service.repository, candidate_session_id)
            ),
            load_validated_bundle_text=self.bundle_text_loader(),
            import_bundle_text=lambda bundle_yaml: service.import_bundle_text(
                bundle_yaml,
                imported_from_path=str(Path(service.get_alignment_session(session_id)["bundle_path"])),
            ),
            start_run=service.start_run,
            start_run_async=service.start_run_async,
            bundle_lifecycle_context=self.bundle_lifecycle_context,
        )

    def message_context(self) -> AlignmentMessageContext:
        service = self.service
        return AlignmentMessageContext(
            get_session=service.get_alignment_session,
            transcript_context=self.transcript_context,
            start_session_async=service.start_alignment_session_async,
        )

    def delete_context(self) -> AlignmentDeleteContext:
        service = self.service
        return AlignmentDeleteContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            append_local_diagnostic_event=self.append_local_diagnostic_event,
            mark_local_asset_cleanup_by_path=service._mark_local_asset_cleanup_by_path,
        )

    def sync_context(self) -> AlignmentSyncContext:
        service = self.service
        return AlignmentSyncContext(
            get_session=service.get_alignment_session,
            load_validated_bundle_text=self.sync_bundle_text_loader(),
            append_notice_message=alignment_notice_appender(self.transcript_context()),
            bundle_lifecycle_context=self.bundle_lifecycle_context,
            build_preview=service._bundle_preview_payload,
        )

    def bundle_text_loader(self) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
        return alignment_validated_bundle_text_loader(AlignmentBundleTextValidationContext())

    def sync_bundle_text_loader(self) -> Callable[[dict, str, list[str]], tuple[dict, str]]:
        service = self.service

        def load_bundle(session: dict, bundle_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
            candidate_event = agent_recovery_agent_entry_candidate_event(service.repository, str(session.get("id") or ""))
            payload = candidate_event.get("payload") if isinstance(candidate_event.get("payload"), dict) else {}
            has_agent_candidate_yaml = payload.get("has_candidate_yaml") is True
            context = AlignmentBundleTextValidationContext(
                include_agent_candidate_loop_fit_contradiction=has_agent_candidate_yaml,
                include_agent_candidate_contract_issues=has_agent_candidate_yaml,
            )
            return alignment_validated_bundle_text_loader(context)(session, bundle_yaml, semantic_issues)

        return load_bundle

    def session_lifecycle_context(self) -> AlignmentSessionLifecycleContext:
        service = self.service

        def execute_session(session_id: str) -> None:
            execute_alignment_session(
                self.session_orchestration_context(),
                session_id,
                logger=self.logger,
            )

        return AlignmentSessionLifecycleContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
            execute_session=execute_session,
            threads=service._threads,
            thread_key=alignment_thread_key,
            append_diagnostic_event=self.append_diagnostic_event,
            signal_process=os.kill,
        )

    def session_orchestration_context(self) -> AlignmentSessionOrchestrationContext:
        return alignment_session_orchestration_context(self.service, self)

    def transcript_context(self) -> AlignmentTranscriptContext:
        service = self.service
        return AlignmentTranscriptContext(
            repository=service.repository,
            get_session=service.get_alignment_session,
        )

    def run_context_resolver_context(self) -> AlignmentRunContextResolverContext:
        return build_alignment_run_context_resolver_context(self.service)

    def workdir_context_resolver_context(self) -> AlignmentWorkdirContextResolverContext:
        return build_alignment_workdir_context_resolver_context(self.service)

    def loopora_context_resolver_context(self) -> AlignmentLooporaContextResolverContext:
        return build_alignment_loopora_context_resolver_context(self.service)
