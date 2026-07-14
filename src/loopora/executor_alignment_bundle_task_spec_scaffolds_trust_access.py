from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_auth_session_token_lifecycle_task,
    _is_authorization_policy_task,
    _is_identity_sso_task,
    _is_support_impersonation_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_authorization_policy_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_authorization_policy_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="authorization_policy",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_support_impersonation_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_support_impersonation_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="support_impersonation",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_identity_sso_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_identity_sso_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="identity_sso",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_auth_session_token_lifecycle_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_auth_session_token_lifecycle_task,
        "auth_session_token_lifecycle",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
