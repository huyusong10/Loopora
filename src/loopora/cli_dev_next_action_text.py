from __future__ import annotations


def dev_check_next_summary(result: dict) -> str:
    actions = [action for action in list(result.get("next_actions") or []) if isinstance(action, dict)]
    rendered = [text for action in actions if (text := dev_check_next_action_text(action))]
    return "; ".join(rendered) if rendered else "none"


def dev_check_next_action_text(action: dict) -> str:
    kind = str(action.get("kind") or "").strip()
    command = str(action.get("command") or "").strip()
    if kind in {"run_recommended_focused_checks", "run_remaining_recommended_focused_checks", "run_selected_focused_checks"}:
        text = _dev_check_focused_run_action_text(action, command=command)
    elif kind == "review_focused_check_guide":
        text = _dev_check_review_focused_guide_action_text(command=command)
    elif kind == "review_unmatched_changed_files":
        text = _dev_check_review_unmatched_action_text(action)
    elif kind == "review_ignored_changed_files":
        text = _dev_check_review_ignored_action_text(action)
    elif kind == "focused_checks_passed":
        text = f"focused checks passed{dev_check_guide_suffix(action)}"
    elif kind == "fix_failed_step":
        text = _dev_check_fix_failed_step_action_text(action)
    elif kind in {"run_default_fast_gate", "run_final_pr_evidence_gate", "rerun_focused_checks", "rerun_default_fast_gate"}:
        text = _dev_check_command_action_text(kind, command=command)
    else:
        text = _DEV_CHECK_SIMPLE_NEXT_ACTION_TEXT.get(kind, "")
    return text


def dev_check_guide_suffix(action: dict) -> str:
    guide_ids = [str(item) for item in list(action.get("guide_ids") or []) if str(item).strip()]
    if not guide_ids:
        return ""
    if len(guide_ids) <= 3:
        return f" ({', '.join(guide_ids)})"
    visible_ids = ", ".join(guide_ids[:3])
    return f" ({len(guide_ids)} guides: {visible_ids}, +{len(guide_ids) - 3} more)"


def dev_check_file_list_summary(files: list[str], source: dict) -> str:
    visible = files[:4]
    omitted = int(source.get("omitted_matched_file_count") or source.get("omitted_file_count") or 0)
    if not omitted:
        matched_file_count = int(source.get("matched_file_count") or source.get("file_count") or len(files))
        omitted = max(matched_file_count - len(visible), 0)
    suffix = f" (+{omitted} more)" if omitted else ""
    return f"{', '.join(visible)}{suffix}"


_DEV_CHECK_SIMPLE_NEXT_ACTION_TEXT = {
    "no_recommended_focused_checks": "no recommended focused checks for current changes",
    "default_fast_gate_passed": "default-fast gate passed",
    "pr_evidence_ready": "PR evidence is ready to copy",
}


def _dev_check_command_action_text(kind: str, *, command: str) -> str:
    fallback = {
        "run_default_fast_gate": "run the default-fast gate",
        "run_final_pr_evidence_gate": "run the final PR evidence gate",
        "rerun_focused_checks": "rerun focused checks",
        "rerun_default_fast_gate": "rerun the default-fast gate",
    }.get(kind, "")
    verb = "rerun" if kind.startswith("rerun_") else "run"
    return f"{verb} {command}" if command else fallback


def _dev_check_fix_failed_step_action_text(action: dict) -> str:
    failed_step = action.get("failed_step") if isinstance(action.get("failed_step"), dict) else {}
    step_id = str(action.get("step_id") or failed_step.get("id") or "").strip()
    returncode = failed_step.get("returncode")
    command = str(failed_step.get("command") or "").strip()
    code_text = f" (exit {returncode})" if returncode is not None else ""
    base = f"fix the failed step {step_id}{code_text}" if step_id else f"fix the failed step{code_text}"
    return f"{base}: {command}" if command else base


def _dev_check_focused_run_action_text(action: dict, *, command: str) -> str:
    kind = str(action.get("kind") or "").strip()
    fallback = "run selected focused checks"
    if kind == "run_recommended_focused_checks":
        fallback = "run the recommended focused checks for the touched boundary"
    elif kind == "run_remaining_recommended_focused_checks":
        fallback = "run the remaining recommended focused checks"
    suffix = dev_check_guide_suffix(action)
    return f"run {command}{suffix}" if command else f"{fallback}{suffix}"


def _dev_check_review_unmatched_action_text(action: dict) -> str:
    files = [str(path) for path in list(action.get("files") or []) if str(path).strip()]
    if not files:
        return "review changed files that did not match a focused guide"
    return (
        f"review unmatched changed files ({dev_check_file_list_summary(files, action)}) "
        "and choose additional focused, journey, review, or probe evidence if needed"
    )


def _dev_check_review_ignored_action_text(action: dict) -> str:
    files = [str(path) for path in list(action.get("files") or []) if str(path).strip()]
    if not files:
        return "review ignored changed-file inputs"
    return f"review ignored changed-file inputs ({dev_check_file_list_summary(files, action)}) and pass project-relative paths or paths under --workdir"


def _dev_check_review_focused_guide_action_text(*, command: str) -> str:
    fallback = "choose a focused check from the guide when the touched boundary needs local evidence"
    return f"inspect the focused check guide: {command}" if command else fallback
