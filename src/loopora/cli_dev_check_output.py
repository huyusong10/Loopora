from __future__ import annotations

import typer

from loopora.cli_dev_next_action_text import dev_check_file_list_summary, dev_check_guide_suffix, dev_check_next_action_text
from loopora.dev_check import DEFAULT_FAST_PROFILE, FOCUSED_PROFILE


def print_dev_check_result(result: dict) -> None:
    profile = str(result.get("profile") or DEFAULT_FAST_PROFILE)
    status = str(result.get("status") or "unknown")
    typer.echo(f"Loopora dev check: {profile}")
    typer.echo(f"status: {status}")
    typer.echo(f"workdir: {result.get('workdir')}")
    if status == "listed":
        _print_changed_file_detection(result)
        _print_ignored_changed_files(result)
        _print_focused_selection_choices(result)
        _print_recommended_focused_guides(result)
        _print_unmatched_changed_files(result)
        _print_dev_check_pr_evidence_hint(result)
        _print_dev_check_steps(result)
        _print_focused_check_guides(result)
        _print_dev_check_next_actions(result)
    elif status in {"pass", "fail", "skipped"}:
        if profile == FOCUSED_PROFILE:
            _print_changed_file_detection(result)
            _print_ignored_changed_files(result)
            if result.get("selected_focused_guides"):
                _print_selected_focused_guides(result)
                _print_unselected_recommended_focused_guides(result)
            else:
                _print_recommended_focused_guides(result)
            _print_unmatched_changed_files(result)
        elif profile == DEFAULT_FAST_PROFILE:
            _print_changed_file_detection(result)
            _print_ignored_changed_files(result)
            _print_recommended_focused_guides(result)
            _print_unmatched_changed_files(result)
        _print_dev_check_steps(result)
        _print_dev_check_next_actions(result)


def print_dev_check_progress(event: dict) -> None:
    event_kind = str(event.get("event") or "").strip()
    step_id = str(event.get("id") or "").strip()
    command = str(event.get("command") or "").strip()
    if event_kind == "step_started":
        suffix = f" - {command}" if command else ""
        typer.echo(f"progress: running {step_id}{suffix}")
        return
    if event_kind == "step_finished":
        status = str(event.get("status") or "").strip() or "done"
        duration = event.get("duration_seconds")
        duration_text = f" ({duration}s)" if duration is not None else ""
        typer.echo(f"progress: {status} {step_id}{duration_text}")
        return
    if event_kind == "step_skipped":
        typer.echo(f"progress: skipped {step_id}")


def _print_dev_check_steps(result: dict) -> None:
    steps = [step for step in list(result.get("steps") or []) if isinstance(step, dict)]
    for step in steps:
        line = f"- {step.get('status')}: {step.get('id')} - {step.get('command')}"
        typer.echo(line)
        if step.get("status") == "fail":
            stderr = str(step.get("stderr") or "").strip()
            stdout = str(step.get("stdout") or "").strip()
            if stdout:
                typer.echo("  stdout:")
                typer.echo(_indent_block(stdout))
            if stderr:
                typer.echo("  stderr:")
                typer.echo(_indent_block(stderr))


def _indent_block(text: str) -> str:
    return "\n".join(f"    {line}" for line in str(text).splitlines())


def _print_dev_check_next_actions(result: dict) -> None:
    actions = [action for action in list(result.get("next_actions") or []) if isinstance(action, dict)]
    rendered = [dev_check_next_action_text(action) for action in actions]
    rendered = [item for item in rendered if item]
    if not rendered:
        return
    typer.echo(f"next: {'; '.join(rendered)}")


def _print_dev_check_pr_evidence_hint(result: dict) -> None:
    recommended_ids = [
        str(guide.get("id") or "").strip()
        for guide in list(result.get("recommended_focused_guides") or [])
        if isinstance(guide, dict) and str(guide.get("id") or "").strip()
    ]
    if recommended_ids:
        guide_summary = dev_check_guide_suffix({"guide_ids": recommended_ids})
        typer.echo(f"PR evidence: record recommended guide IDs{guide_summary}, ignored changed files, and unmatched changed files before choosing checks.")
        return
    typer.echo("PR evidence: record the changed-file detection status, ignored changed files, and unmatched changed files before choosing checks.")


def _print_changed_file_detection(result: dict) -> None:
    detection = result.get("changed_file_detection") if isinstance(result.get("changed_file_detection"), dict) else {}
    status = str(detection.get("status") or "unknown").strip() or "unknown"
    source = str(detection.get("source") or "unknown").strip() or "unknown"
    count = int(detection.get("count") or 0)
    labels = {
        ("git", "detected"): "Git changes detected",
        ("git", "clean"): "Git tree clean",
        ("git", "unavailable"): "Git changed-file detection unavailable",
        ("provided", "provided"): "provided changed files",
    }
    label = labels.get((source, status), f"{source} {status}")
    typer.echo(f"changes: {label} ({count} file(s))")


def _print_focused_check_guides(result: dict) -> None:
    guides = [guide for guide in list(result.get("focused_guides") or []) if isinstance(guide, dict)]
    if not guides:
        return
    typer.echo("focused check guide:")
    for guide in guides:
        typer.echo(f"- {guide.get('id')}: {guide.get('command')}")
        when = str(guide.get("when") or "").strip()
        evidence_type = str(guide.get("evidence_type") or "").strip()
        details = f"{evidence_type}: {when}" if evidence_type else when
        if details:
            typer.echo(f"  when: {details}")


def _print_focused_selection_choices(result: dict) -> None:
    choices = [str(item) for item in list(result.get("focused_selection_choices") or []) if str(item).strip()]
    if choices:
        typer.echo(f"focused selectors: {', '.join(choices)}")


def _print_recommended_focused_guides(result: dict) -> None:
    guides = [guide for guide in list(result.get("recommended_focused_guides") or []) if isinstance(guide, dict)]
    if not guides:
        _print_no_recommended_focused_guides_reason(result)
        return
    typer.echo("recommended focused checks for current changes:")
    _print_compact_focused_guide_lines(guides)


def _print_selected_focused_guides(result: dict) -> None:
    guides = [guide for guide in list(result.get("selected_focused_guides") or []) if isinstance(guide, dict)]
    if not guides:
        return
    typer.echo("selected focused checks:")
    _print_compact_focused_guide_lines(guides)


def _print_unselected_recommended_focused_guides(result: dict) -> None:
    selected_ids = {str(guide.get("id") or "").strip() for guide in list(result.get("selected_focused_guides") or []) if isinstance(guide, dict)}
    selected_ids.update(str(guide_id).strip() for guide_id in list(result.get("focused_ran_guide_ids") or []) if str(guide_id).strip())
    recommended_ids = [str(guide.get("id") or "").strip() for guide in list(result.get("recommended_focused_guides") or []) if isinstance(guide, dict)]
    unselected_ids = [guide_id for guide_id in recommended_ids if guide_id and guide_id not in selected_ids]
    if unselected_ids:
        typer.echo(f"other recommended focused checks for current changes: {', '.join(unselected_ids)}")


def _print_compact_focused_guide_lines(guides: list[dict]) -> None:
    for guide in guides:
        typer.echo(_recommended_focused_guide_line(guide))
        matched_files = [str(path) for path in list(guide.get("matched_files") or []) if str(path).strip()]
        if matched_files:
            typer.echo(f"  matched: {_matched_files_summary(matched_files, guide)}")


def _recommended_focused_guide_line(guide: dict) -> str:
    guide_id = str(guide.get("id") or "").strip() or "unknown"
    label = str(guide.get("label") or "").strip()
    evidence_type = str(guide.get("evidence_type") or "").strip()
    prefix = f"- {guide_id}"
    if evidence_type:
        prefix = f"{prefix} ({evidence_type})"
    return f"{prefix}: {label}" if label else prefix


def _matched_files_summary(matched_files: list[str], guide: dict) -> str:
    return dev_check_file_list_summary(matched_files, guide)


def _print_unmatched_changed_files(result: dict) -> None:
    count = int(result.get("unmatched_changed_file_count") or 0)
    if count <= 0:
        changed_file_detection = result.get("changed_file_detection") if isinstance(result.get("changed_file_detection"), dict) else {}
        changed_count = int(changed_file_detection.get("count") or 0)
        if changed_count > 0:
            typer.echo("unmatched changed files: none")
        return
    files = [str(path) for path in list(result.get("unmatched_changed_files") or []) if str(path).strip()]
    omitted = int(result.get("omitted_unmatched_changed_file_count") or 0)
    typer.echo(f"unmatched changed files: {dev_check_file_list_summary(files, {'file_count': count, 'omitted_file_count': omitted})}")
    typer.echo("  note: choose additional focused, journey, review, or probe evidence when these files affect a stable boundary.")


def _print_ignored_changed_files(result: dict) -> None:
    count = int(result.get("ignored_changed_file_count") or 0)
    if count <= 0:
        changed_file_detection = result.get("changed_file_detection") if isinstance(result.get("changed_file_detection"), dict) else {}
        changed_count = int(changed_file_detection.get("count") or 0)
        if changed_count > 0:
            typer.echo("ignored changed files: none")
        return
    files = [str(path) for path in list(result.get("ignored_changed_files") or []) if str(path).strip()]
    omitted = int(result.get("omitted_ignored_changed_file_count") or 0)
    typer.echo(f"ignored changed files: {dev_check_file_list_summary(files, {'file_count': count, 'omitted_file_count': omitted})}")
    typer.echo("  note: ignored paths are outside --workdir or parent-relative; pass project-relative paths or paths under --workdir.")


def _print_no_recommended_focused_guides_reason(result: dict) -> None:
    detection = result.get("changed_file_detection") if isinstance(result.get("changed_file_detection"), dict) else {}
    reason_info = result.get("no_recommended_focused_check_reason") if isinstance(result.get("no_recommended_focused_check_reason"), dict) else {}
    status = str(detection.get("status") or "").strip()
    count = int(detection.get("count") or 0)
    reason_code = str(reason_info.get("reason") or "").strip()
    if reason_code == "git_clean" or status == "clean":
        reason = "no current Git changes detected"
    elif reason_code == "git_unavailable" or status == "unavailable":
        reason = "Git changed-file detection is unavailable for this workdir"
    elif reason_code == "unmatched_changed_files" or count:
        count = int(reason_info.get("changed_file_count") or count)
        reason = f"{count} changed file(s) did not match a focused guide"
    elif reason_code == "ignored_changed_files":
        count = int(reason_info.get("ignored_changed_file_count") or 0)
        reason = f"{count} changed-file input(s) were ignored"
    else:
        reason = "no changed files provided"
    typer.echo(f"recommended focused checks for current changes: none ({reason})")
