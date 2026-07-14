from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_feature_flag_rollout_task,
    _is_incident_root_cause_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)


def _append_feature_flag_rollout_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_feature_flag_rollout_task,
        "feature_flag_rollout",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_incident_root_cause_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_incident_root_cause_task,
        "incident_root_cause",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
