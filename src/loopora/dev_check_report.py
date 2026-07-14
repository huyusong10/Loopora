from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.dev_check_focus import focused_check_selection_choices
from loopora.dev_check_focus import listed_focused_guide
from loopora.dev_check_focus import recommended_focused_guides
from loopora.dev_check_focus import unmatched_changed_files
from loopora.dev_check_guides import FOCUSED_CHECK_GUIDES
from loopora.dev_check_next_actions import declared_focused_run_guide_ids
from loopora.dev_check_next_actions import dev_check_next_actions
from loopora.dev_check_next_actions import failed_step_summary
from loopora.dev_check_next_actions import no_recommended_focused_check_reason
from loopora.dev_check_types import DEV_CHECK_SCHEMA_VERSION
from loopora.dev_check_types import DevCheckReportContext


def build_dev_check_report(
    root: Path,
    *,
    context: DevCheckReportContext,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    failed_step = next((step for step in steps if step.get("status") == "fail"), None)
    failed_summary = failed_step_summary(failed_step)
    focused_guides = [listed_focused_guide(guide) for guide in FOCUSED_CHECK_GUIDES]
    changed_file_detection = context.changed_file_detection
    changed_files = changed_file_detection.files
    ignored_files = list(changed_file_detection.ignored_files)
    recommended_guides = recommended_focused_guides(focused_guides, changed_files)
    unmatched_files = unmatched_changed_files(focused_guides, changed_files)
    focused_ran_guide_ids = declared_focused_run_guide_ids(context, recommended_guides=recommended_guides)
    visible_unmatched_files = unmatched_files[:12]
    visible_ignored_files = ignored_files[:12]
    selected_guides = list(context.selected_focused_guides)
    no_recommended_reason = no_recommended_focused_check_reason(changed_file_detection, unmatched_files=unmatched_files) if not recommended_guides else {}
    next_actions = dev_check_next_actions(
        context=context,
        failed_step=failed_step,
        recommended_guides=recommended_guides,
        unmatched_files=unmatched_files,
        no_recommended_reason=no_recommended_reason,
    )
    payload = {
        "dev_check_summary": {
            "schema_version": DEV_CHECK_SCHEMA_VERSION,
            "profile": context.profile,
            "status": context.status,
            "ready": context.status in {"listed", "pass", "skipped"},
            "workdir": str(root),
            "step_count": len(steps),
            "focused_guide_count": len(focused_guides),
            "focused_selection": context.focused_selection,
            "selected_focused_guide_count": len(selected_guides),
            "focused_ran_guide_ids": focused_ran_guide_ids,
            "changed_file_count": len(changed_files),
            "changed_file_source": changed_file_detection.source,
            "changed_file_status": changed_file_detection.status,
            "ignored_changed_file_count": len(ignored_files),
            "recommended_focused_guide_count": len(recommended_guides),
            "no_recommended_focused_check_reason": str(no_recommended_reason.get("reason") or ""),
            "unmatched_changed_file_count": len(unmatched_files),
            "failed_step_id": failed_step.get("id") if failed_step else "",
            "failed_step": failed_summary,
            "next_action_kinds": [action["kind"] for action in next_actions],
        },
        "schema_version": DEV_CHECK_SCHEMA_VERSION,
        "profile": context.profile,
        "status": context.status,
        "ready": context.status in {"listed", "pass", "skipped"},
        "workdir": str(root),
        "steps": steps,
        "focused_guides": focused_guides,
        "focused_selection_choices": list(focused_check_selection_choices()),
        "focused_selection": context.focused_selection,
        "selected_focused_guides": selected_guides,
        "focused_ran_guide_ids": focused_ran_guide_ids,
        "changed_files": changed_files,
        "changed_file_detection": {
            "source": changed_file_detection.source,
            "status": changed_file_detection.status,
            "count": len(changed_files),
        },
        "recommended_focused_guides": recommended_guides,
        "no_recommended_focused_check_reason": no_recommended_reason,
        "ignored_changed_files": visible_ignored_files,
        "ignored_changed_file_count": len(ignored_files),
        "omitted_ignored_changed_file_count": len(ignored_files) - len(visible_ignored_files),
        "unmatched_changed_files": visible_unmatched_files,
        "unmatched_changed_file_count": len(unmatched_files),
        "omitted_unmatched_changed_file_count": len(unmatched_files) - len(visible_unmatched_files),
        "failed_step": failed_summary,
        "next_actions": next_actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="dev_check_summary")
