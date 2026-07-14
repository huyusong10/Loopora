from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_data_residency_task,
    _is_kyc_aml_screening_task,
)
from loopora.executor_alignment_bundle_task_spec_scaffold_templates import apply_task_spec_scaffold_template_from_asset


def _append_data_residency_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_data_residency_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="data_residency",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _append_kyc_aml_screening_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    if not _is_kyc_aml_screening_task(task):
        return
    apply_task_spec_scaffold_template_from_asset(
        bundle,
        template_key="kyc_aml_screening",
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )
