from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.dev_check_changed_files import changed_file_detection as _changed_file_detection
from loopora.dev_check_execution import CommandRunner
from loopora.dev_check_execution import ProgressReporter
from loopora.dev_check_execution import emit_dev_check_progress as _emit_dev_check_progress
from loopora.dev_check_execution import listed_step as _listed_step
from loopora.dev_check_execution import run_default_step as _run_default_step
from loopora.dev_check_execution import run_focused_step as _run_focused_step
from loopora.dev_check_execution import run_subprocess
from loopora.dev_check_focus import (
    DEFAULT_FOCUSED_SELECTION as DEFAULT_FOCUSED_SELECTION,
    focused_check_selection_choices as focused_check_selection_choices,
    focused_check_selection_help as focused_check_selection_help,
    focused_ran_tokens as _focused_ran_tokens,
    listed_focused_guide as _listed_focused_guide,
    listed_focused_step as _listed_focused_step,
    recommended_focused_guides as _recommended_focused_guides,
    selected_focused_guides as _selected_focused_guides,
)
from loopora.dev_check_guides import DEFAULT_FAST_COMMANDS, FOCUSED_CHECK_GUIDES
from loopora.dev_check_report import build_dev_check_report
from loopora.dev_check_types import DEFAULT_FAST_PROFILE
from loopora.dev_check_types import DEV_CHECK_SCHEMA_VERSION as DEV_CHECK_SCHEMA_VERSION
from loopora.dev_check_types import FOCUSED_PROFILE
from loopora.dev_check_types import ChangedFileDetection
from loopora.dev_check_types import DevCheckCommandResult as DevCheckCommandResult
from loopora.dev_check_types import DevCheckReportContext
from loopora.service_types import LooporaError
from loopora.workdir_inputs import normalize_existing_workdir


def run_dev_check(  # noqa: PLR0913 - public dev-check API keeps explicit execution controls
    *,
    workdir: Path | str,
    profile: str = DEFAULT_FAST_PROFILE,
    list_only: bool = False,
    command_runner: CommandRunner | None = None,
    changed_files: list[str] | None = None,
    focused: str | None = None,
    focused_ran: list[str] | None = None,
    progress_reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    root = normalize_existing_workdir(workdir)
    normalized_profile = str(profile or "").strip() or DEFAULT_FAST_PROFILE
    normalized_focus = _normalized_focused_selection(focused)
    normalized_focused_ran = () if list_only else _focused_ran_tokens(focused_ran)
    if normalized_profile == FOCUSED_PROFILE and not normalized_focus:
        normalized_focus = DEFAULT_FOCUSED_SELECTION
    if normalized_profile not in {DEFAULT_FAST_PROFILE, FOCUSED_PROFILE}:
        raise LooporaError(f"unsupported dev check profile: {profile!r}. Expected: {DEFAULT_FAST_PROFILE} or {FOCUSED_PROFILE}")
    changed_file_detection = _changed_file_detection(changed_files, root=root)
    if normalized_focus:
        return _run_focused_dev_check(
            root,
            focus_selection=normalized_focus,
            list_only=list_only,
            command_runner=command_runner,
            changed_file_detection=changed_file_detection,
            focused_ran_tokens=normalized_focused_ran,
            progress_reporter=progress_reporter,
        )
    if normalized_profile == FOCUSED_PROFILE:
        return _run_focused_dev_check(
            root,
            focus_selection=DEFAULT_FOCUSED_SELECTION,
            list_only=list_only,
            command_runner=command_runner,
            changed_file_detection=changed_file_detection,
            focused_ran_tokens=normalized_focused_ran,
            progress_reporter=progress_reporter,
        )

    steps = [_listed_step(command) for command in DEFAULT_FAST_COMMANDS]
    if list_only:
        return build_dev_check_report(
            root,
            context=DevCheckReportContext(
                workdir=root,
                profile=normalized_profile,
                status="listed",
                changed_file_detection=changed_file_detection,
                focused_ran_tokens=normalized_focused_ran,
            ),
            steps=steps,
        )

    runner = command_runner or _run_subprocess
    executed_steps: list[dict[str, Any]] = []
    failed = False
    for command in DEFAULT_FAST_COMMANDS:
        if failed:
            skipped = _listed_step(command)
            skipped["status"] = "skipped"
            executed_steps.append(skipped)
            _emit_dev_check_progress(progress_reporter, event="step_skipped", step=skipped)
            continue
        step = _run_default_step(root, command, runner=runner, progress_reporter=progress_reporter)
        executed_steps.append(step)
        failed = step["status"] != "pass"
    return build_dev_check_report(
        root,
        context=DevCheckReportContext(
            workdir=root,
            profile=normalized_profile,
            status="fail" if failed else "pass",
            changed_file_detection=changed_file_detection,
            focused_ran_tokens=normalized_focused_ran,
        ),
        steps=executed_steps,
    )


def _run_focused_dev_check(  # noqa: PLR0913 - focused execution keeps selection, evidence, and runner inputs explicit.
    root: Path,
    *,
    focus_selection: str,
    list_only: bool,
    command_runner: CommandRunner | None,
    changed_file_detection: ChangedFileDetection,
    focused_ran_tokens: tuple[str, ...] = (),
    progress_reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    focused_guides = [_listed_focused_guide(guide) for guide in FOCUSED_CHECK_GUIDES]
    recommended_guides = _recommended_focused_guides(focused_guides, changed_file_detection.files)
    selected_guides = _selected_focused_guides(
        focus_selection,
        focused_guides=focused_guides,
        recommended_guides=recommended_guides,
    )
    steps = [_listed_focused_step(guide) for guide in selected_guides]
    if list_only:
        return build_dev_check_report(
            root,
            context=DevCheckReportContext(
                workdir=root,
                profile=FOCUSED_PROFILE,
                status="listed",
                changed_file_detection=changed_file_detection,
                focused_selection=focus_selection,
                selected_focused_guides=tuple(selected_guides),
            ),
            steps=steps,
        )
    if not selected_guides:
        return build_dev_check_report(
            root,
            context=DevCheckReportContext(
                workdir=root,
                profile=FOCUSED_PROFILE,
                status="skipped",
                changed_file_detection=changed_file_detection,
                focused_selection=focus_selection,
            ),
            steps=[],
        )

    runner = command_runner or _run_subprocess
    executed_steps: list[dict[str, Any]] = []
    failed = False
    for guide in selected_guides:
        if failed:
            skipped = _listed_focused_step(guide)
            skipped["status"] = "skipped"
            executed_steps.append(skipped)
            _emit_dev_check_progress(progress_reporter, event="step_skipped", step=skipped)
            continue
        step = _run_focused_step(root, guide, runner=runner, progress_reporter=progress_reporter)
        executed_steps.append(step)
        failed = step["status"] != "pass"
    return build_dev_check_report(
        root,
        context=DevCheckReportContext(
            workdir=root,
            profile=FOCUSED_PROFILE,
            status="fail" if failed else "pass",
            changed_file_detection=changed_file_detection,
            focused_selection=focus_selection,
            selected_focused_guides=tuple(selected_guides),
            focused_ran_tokens=focused_ran_tokens,
        ),
        steps=executed_steps,
    )


def _normalized_focused_selection(focused: str | None) -> str:
    return str(focused or "").strip()


_run_subprocess = run_subprocess
