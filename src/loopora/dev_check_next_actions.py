from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.dev_check_command_projection import dev_check_default_fast_command as _dev_check_default_fast_command
from loopora.dev_check_command_projection import dev_check_focused_command as _dev_check_focused_command
from loopora.dev_check_command_projection import dev_check_list_command as _project_dev_check_list_command
from loopora.dev_check_focused_evidence_actions import completed_focused_run_guide_ids
from loopora.dev_check_focused_evidence_actions import declared_focused_run_guide_ids
from loopora.dev_check_focused_evidence_actions import final_pr_evidence_gate_action as _final_pr_evidence_gate_action
from loopora.dev_check_focused_evidence_actions import focused_guides_cover_recommended as _focused_guides_cover_recommended
from loopora.dev_check_focused_evidence_actions import pr_evidence_ready_action as _pr_evidence_ready_action
from loopora.dev_check_focused_evidence_actions import recommended_focused_guides_covered as _recommended_focused_guides_covered
from loopora.dev_check_focused_evidence_actions import run_recommended_focused_checks_action as _run_recommended_focused_checks_action
from loopora.dev_check_focused_evidence_actions import run_remaining_recommended_focused_checks_action as _run_remaining_recommended_focused_checks_action
from loopora.dev_check_types import ChangedFileDetection
from loopora.dev_check_types import DevCheckReportContext
from loopora.dev_check_types import FOCUSED_PROFILE


def failed_step_summary(failed_step: dict[str, Any] | None) -> dict[str, Any]:
    if not failed_step:
        return {}
    return {
        "id": str(failed_step.get("id") or "").strip(),
        "label": str(failed_step.get("label") or "").strip(),
        "command": str(failed_step.get("command") or "").strip(),
        "returncode": failed_step.get("returncode"),
    }


def dev_check_next_actions(
    *,
    context: DevCheckReportContext,
    failed_step: dict[str, Any] | None,
    recommended_guides: list[dict[str, Any]],
    unmatched_files: list[str],
    no_recommended_reason: dict[str, Any],
) -> list[dict[str, Any]]:
    if context.profile == FOCUSED_PROFILE:
        return _focused_dev_check_next_actions(
            context=context,
            failed_step=failed_step,
            recommended_guides=recommended_guides,
            ignored_files=list(context.changed_file_detection.ignored_files),
            unmatched_files=unmatched_files,
            no_recommended_reason=no_recommended_reason,
        )
    return _default_dev_check_next_actions(
        context=context,
        failed_step=failed_step,
        recommended_guides=recommended_guides,
        unmatched_files=unmatched_files,
        no_recommended_reason=no_recommended_reason,
    )


def _focused_dev_check_next_actions(  # noqa: PLR0913 - next-action evidence keeps focused/default scope inputs explicit.
    *,
    context: DevCheckReportContext,
    failed_step: dict[str, Any] | None,
    recommended_guides: list[dict[str, Any]],
    ignored_files: list[str],
    unmatched_files: list[str],
    no_recommended_reason: dict[str, Any],
) -> list[dict[str, Any]]:
    provided_changed_files = _provided_changed_files(context)
    focused_command = _focused_check_command(
        context.focused_selection,
        workdir=context.workdir,
        changed_files=provided_changed_files,
    )
    selected_guides = list(context.selected_focused_guides)
    selected_ids = [str(guide.get("id") or "") for guide in selected_guides if guide.get("id")]
    declared_ids = declared_focused_run_guide_ids(context, recommended_guides=recommended_guides)
    completed_ids = completed_focused_run_guide_ids(declared_ids, selected_ids)
    default_fast_action = {"kind": "run_default_fast_gate", "command": _default_fast_command(context.workdir)}
    final_pr_evidence_action = _final_pr_evidence_gate_action(
        context.workdir,
        focused_ran_ids=completed_ids,
        changed_files=provided_changed_files,
    )
    ignored_action = _review_ignored_changed_files_action(ignored_files)
    unmatched_action = _review_unmatched_changed_files_action(unmatched_files)
    selected_covers_recommended = _focused_guides_cover_recommended(
        completed_ids,
        recommended_guides=recommended_guides,
    )
    if context.status == "listed" and selected_guides:
        return _without_empty_actions(
            [
                {"kind": "run_selected_focused_checks", "guide_ids": selected_ids, "command": focused_command},
                ignored_action,
                unmatched_action,
                default_fast_action,
            ]
        )
    if context.status == "listed":
        return _without_empty_actions([ignored_action, unmatched_action, _no_recommended_focused_checks_action(no_recommended_reason), default_fast_action])
    if context.status == "skipped":
        return _without_empty_actions(
            [
                ignored_action,
                unmatched_action,
                _no_recommended_focused_checks_action(no_recommended_reason),
                _review_focused_check_guide_action(context.workdir, changed_files=provided_changed_files),
                default_fast_action,
            ]
        )
    if context.status == "pass":
        return _without_empty_actions(
            [
                {"kind": "focused_checks_passed", "guide_ids": selected_ids},
                ignored_action,
                unmatched_action,
                final_pr_evidence_action
                if selected_covers_recommended
                else _run_remaining_recommended_focused_checks_action(
                    context,
                    recommended_guides=recommended_guides,
                    completed_ids=completed_ids,
                    changed_files=provided_changed_files,
                ),
                default_fast_action,
            ]
        )
    if context.status == "fail":
        return [
            _fix_failed_step_action(failed_step),
            {"kind": "rerun_focused_checks", "command": focused_command},
        ]
    return []


def _default_dev_check_next_actions(
    *,
    context: DevCheckReportContext,
    failed_step: dict[str, Any] | None,
    recommended_guides: list[dict[str, Any]],
    unmatched_files: list[str],
    no_recommended_reason: dict[str, Any],
) -> list[dict[str, Any]]:
    default_fast_command = _default_fast_command(context.workdir)
    ignored_action = _review_ignored_changed_files_action(list(context.changed_file_detection.ignored_files))
    unmatched_action = _review_unmatched_changed_files_action(unmatched_files)
    if context.status == "listed" and recommended_guides:
        return _without_empty_actions(
            [
                ignored_action,
                unmatched_action,
                _run_recommended_focused_checks_action(
                    context,
                    recommended_guides=recommended_guides,
                    changed_files=_provided_changed_files(context),
                ),
                {"kind": "run_default_fast_gate", "command": default_fast_command},
            ]
        )
    if context.status == "listed":
        return _without_empty_actions(
            [
                ignored_action,
                unmatched_action,
                _no_recommended_focused_checks_action(no_recommended_reason),
                {"kind": "review_focused_check_guide"},
                {"kind": "run_default_fast_gate", "command": default_fast_command},
            ]
        )
    if context.status == "pass":
        recommended_covered = _recommended_focused_guides_covered(
            context,
            recommended_guides=recommended_guides,
        )
        return _without_empty_actions(
            [
                {"kind": "default_fast_gate_passed"},
                ignored_action,
                unmatched_action,
                _pr_evidence_ready_action(recommended_guides)
                if recommended_covered
                else _run_recommended_focused_checks_action(
                    context,
                    recommended_guides=recommended_guides,
                    changed_files=_provided_changed_files(context),
                ),
            ]
        )
    if context.status == "fail":
        return [
            _fix_failed_step_action(failed_step),
            {"kind": "rerun_default_fast_gate", "command": default_fast_command},
        ]
    return []


def _fix_failed_step_action(failed_step: dict[str, Any] | None) -> dict[str, Any]:
    summary = failed_step_summary(failed_step)
    return {"kind": "fix_failed_step", "step_id": str(summary.get("id") or ""), "failed_step": summary}


def _review_unmatched_changed_files_action(unmatched_files: list[str]) -> dict[str, Any]:
    visible_files = unmatched_files[:12]
    if not visible_files and not unmatched_files:
        return {}
    return {
        "kind": "review_unmatched_changed_files",
        "files": visible_files,
        "file_count": len(unmatched_files),
        "omitted_file_count": len(unmatched_files) - len(visible_files),
    }


def _review_ignored_changed_files_action(ignored_files: list[str]) -> dict[str, Any]:
    visible_files = ignored_files[:12]
    if not visible_files and not ignored_files:
        return {}
    return {
        "kind": "review_ignored_changed_files",
        "files": visible_files,
        "file_count": len(ignored_files),
        "omitted_file_count": len(ignored_files) - len(visible_files),
    }


def no_recommended_focused_check_reason(
    changed_file_detection: ChangedFileDetection,
    *,
    unmatched_files: list[str],
) -> dict[str, Any]:
    changed_count = len(changed_file_detection.files)
    ignored_count = len(changed_file_detection.ignored_files)
    if changed_file_detection.status == "clean":
        reason = "git_clean"
    elif changed_file_detection.status == "unavailable":
        reason = "git_unavailable"
    elif changed_count == 0 and ignored_count > 0:
        reason = "ignored_changed_files"
    elif changed_count > 0:
        reason = "unmatched_changed_files"
    else:
        reason = "no_changed_files"
    return {
        "reason": reason,
        "changed_file_source": changed_file_detection.source,
        "changed_file_status": changed_file_detection.status,
        "changed_file_count": changed_count,
        "ignored_changed_file_count": ignored_count,
        "unmatched_changed_file_count": len(unmatched_files),
    }


def _no_recommended_focused_checks_action(reason: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "no_recommended_focused_checks", **reason}


def _review_focused_check_guide_action(workdir: Path, *, changed_files: list[str] | None = None) -> dict[str, str]:
    return {"kind": "review_focused_check_guide", "command": _dev_check_list_command(workdir, changed_files=changed_files)}


def _without_empty_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [action for action in actions if action]


def _default_fast_command(workdir: Path) -> str:
    return _dev_check_default_fast_command(workdir)


def _dev_check_list_command(workdir: Path, *, changed_files: list[str] | None = None) -> str:
    return _project_dev_check_list_command(workdir, changed_files=changed_files)


def _focused_check_command(
    focused_selection: str,
    *,
    workdir: Path,
    changed_files: list[str] | None = None,
    focused_ran: list[str] | None = None,
) -> str:
    return _dev_check_focused_command(
        focused_selection,
        workdir=workdir,
        changed_files=changed_files,
        focused_ran=focused_ran,
    )


def _provided_changed_files(context: DevCheckReportContext) -> list[str]:
    if context.changed_file_detection.source != "provided":
        return []
    return list(context.changed_file_detection.files)
