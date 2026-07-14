from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_notification_subscription_deliverability_task,
    _is_schedule_phase_task,
    _is_support_ticket_sla_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_schedule_phase_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_schedule_phase_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="schedule_phase",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_notification_subscription_deliverability_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_notification_subscription_deliverability_task,
        "notification_subscription_deliverability",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_support_ticket_sla_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_support_ticket_sla_task,
        "support_ticket_sla",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
