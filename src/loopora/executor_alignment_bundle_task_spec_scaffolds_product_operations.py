from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_analytics_experiment_instrumentation_task,
    _is_concurrency_conflict_resolution_task,
    _is_inventory_reservation_consistency_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_concurrency_conflict_resolution_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_concurrency_conflict_resolution_task(task):
        return
    if "# Collaborative Conflict Resolution Workflow Notes" in str(bundle.get("spec", {}).get("markdown") or ""):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="concurrency_conflict_resolution",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_analytics_experiment_instrumentation_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_analytics_experiment_instrumentation_task,
        "analytics_experiment_instrumentation",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_inventory_reservation_consistency_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_inventory_reservation_consistency_task,
        "inventory_reservation_consistency",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
