from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_key_rotation_task,
    _is_prompt_asset_ownership_task,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_key_rotation_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_key_rotation_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="key_rotation",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_prompt_asset_ownership_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_prompt_asset_ownership_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="prompt_asset_ownership",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )
