from __future__ import annotations

from loopora.executor_alignment_bundle_task_visible_scaffold_assets import apply_task_visible_scaffold_from_asset


def _replace_schedule_phase_visible_scaffold(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    apply_task_visible_scaffold_from_asset(
        bundle,
        scaffold_key="schedule_phase",
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
