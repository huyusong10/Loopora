from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import (
    bundle_to_yaml,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
    load_bundle_text,
)
from loopora.service_alignment_execution import alignment_bundle_executor_settings_issues
from loopora.service_alignment_language import (
    alignment_bundle_language_issues,
    alignment_generation_display_language,
    alignment_generation_prefers_chinese,
)
from loopora.service_alignment_ready_bundle_validation import alignment_assert_bundle_workdir
from loopora.service_alignment_stage import (
    alignment_bundle_workdir_fact_issues,
    alignment_improvement_bundle_issues,
)
from loopora.service_alignment_traceability_projection import alignment_session_user_task_text
from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot
from loopora.service_bundle_control_summary import build_bundle_control_summary
from loopora.service_types import LooporaError


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
