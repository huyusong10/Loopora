from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_rag_long_chain_task,
    _is_search_index_consistency_task,
    _is_search_quality_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_search_index_consistency_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_search_index_consistency_task(task):
        return
    if _spec_markdown_contains(bundle, "# Search Index Consistency Workflow Notes"):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="search_index_consistency",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_search_quality_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_search_quality_task(task):
        return
    if _spec_markdown_contains(bundle, "# Search Quality Workflow Notes"):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="search_quality",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_rag_long_chain_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_rag_long_chain_task,
        "rag_long_chain",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _spec_markdown_contains(bundle: dict, marker: str) -> bool:
    return marker in str(bundle.get("spec", {}).get("markdown") or "")
