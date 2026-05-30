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
from loopora.service_alignment_context import (
    alignment_assert_bundle_workdir,
    alignment_generation_prefers_chinese,
    alignment_workdir_snapshot,
)
from loopora.service_alignment_execution import alignment_bundle_executor_settings_issues
from loopora.service_alignment_stage import (
    alignment_bundle_language_issues,
    alignment_bundle_workdir_fact_issues,
    alignment_improvement_bundle_issues,
    alignment_session_user_task_text,
)
from loopora.service_types import LooporaError


@dataclass(frozen=True)
class AlignmentBundleTextValidationContext:
    has_agent_candidate_yaml: Callable[[str], bool]


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
            has_agent_candidate_yaml=context.has_agent_candidate_yaml(str(session.get("id") or "")),
        )

    return load_bundle


def alignment_bundle_validation_issues(
    session: dict,
    bundle: dict,
    *,
    has_agent_candidate_yaml: bool,
) -> list[str]:
    issue_sources = (
        lint_alignment_bundle_semantics(bundle),
        alignment_bundle_executor_settings_issues(session, bundle),
        alignment_bundle_language_issues(
            bundle,
            prefers_chinese=alignment_generation_prefers_chinese(session),
        ),
        alignment_bundle_workdir_fact_issues(
            bundle,
            workdir_snapshot=alignment_workdir_snapshot(Path(session["workdir"])),
        ),
        alignment_improvement_bundle_issues(session.get("working_agreement"), bundle),
        alignment_bundle_agreement_traceability_issues(session, bundle),
        (
            alignment_agent_candidate_traceability_issues(
                alignment_session_user_task_text(session),
                bundle,
            )
            if has_agent_candidate_yaml
            else []
        ),
    )
    issues: list[str] = []
    for source_issues in issue_sources:
        extend_unique_alignment_issues(issues, source_issues)
    return issues


def load_validated_alignment_bundle_text(
    session: dict,
    bundle_yaml: str,
    semantic_issues: list[str],
    *,
    has_agent_candidate_yaml: bool,
) -> tuple[dict, str]:
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
            has_agent_candidate_yaml=has_agent_candidate_yaml,
        ),
    )
    if semantic_issues:
        raise LooporaError("bundle semantic lint failed: " + "; ".join(semantic_issues))

    return bundle, bundle_to_yaml(bundle)
