from __future__ import annotations

from loopora.executor_alignment_bundle_task_visible_scaffold_assets import apply_task_visible_scaffold_from_asset


def _replace_data_residency_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    apply_task_visible_scaffold_from_asset(
        bundle,
        scaffold_key="data_residency",
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def _replace_support_impersonation_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    apply_task_visible_scaffold_from_asset(
        bundle,
        scaffold_key="support_impersonation",
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def _replace_kyc_aml_screening_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    apply_task_visible_scaffold_from_asset(
        bundle,
        scaffold_key="kyc_aml_screening",
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def _replace_key_rotation_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    apply_task_visible_scaffold_from_asset(
        bundle,
        scaffold_key="key_rotation",
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
