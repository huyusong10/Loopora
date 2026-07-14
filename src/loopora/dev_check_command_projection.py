from __future__ import annotations

from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.dev_check_focus import DEFAULT_FOCUSED_SELECTION
from loopora.dev_check_focus import focused_selection_tokens as _focused_selection_tokens


def copyable_dev_check_command(args: str = "") -> str:
    suffix = str(args or "").strip()
    command = "loopora dev check"
    if suffix:
        command = f"{command} {suffix}"
    return copyable_loopora_command(command)


def dev_check_default_fast_command(workdir: Path) -> str:
    return _command_with_workdir(copyable_dev_check_command(), workdir=workdir)


def dev_check_list_command(workdir: Path, *, changed_files: list[str] | None = None) -> str:
    return dev_check_command("--list", workdir=workdir, changed_files=changed_files)


def dev_check_focused_command(
    focused_selection: str,
    *,
    workdir: Path,
    changed_files: list[str] | None = None,
    focused_ran: list[str] | None = None,
) -> str:
    selection = str(focused_selection or "").strip() or DEFAULT_FOCUSED_SELECTION
    return dev_check_command(
        _focused_selection_args(selection),
        workdir=workdir,
        changed_files=changed_files,
        focused_ran=focused_ran,
    )


def dev_check_final_pr_evidence_command(
    workdir: Path,
    *,
    focused_ran_ids: list[str],
    changed_files: list[str] | None = None,
) -> str:
    return dev_check_command(
        "--pr-evidence",
        workdir=workdir,
        changed_files=changed_files,
        focused_ran=focused_ran_ids,
    )


def dev_check_command(
    args: str = "",
    *,
    workdir: Path,
    changed_files: list[str] | None = None,
    focused_ran: list[str] | None = None,
) -> str:
    command = copyable_dev_check_command(args)
    command = _command_with_changed_files(command, changed_files)
    command = _command_with_focused_ran(command, focused_ran)
    return _command_with_workdir(command, workdir=workdir)


def _focused_selection_args(selection: str) -> str:
    tokens = _focused_selection_tokens(selection) or [DEFAULT_FOCUSED_SELECTION]
    return " ".join(f"--focused {shlex.quote(token)}" for token in tokens)


def _command_with_changed_files(command: str, changed_files: list[str] | None) -> str:
    paths = [str(path).strip() for path in list(changed_files or []) if str(path).strip()]
    if not paths:
        return command
    args = " ".join(f"--changed-file {shlex.quote(path)}" for path in paths)
    return f"{command} {args}"


def _command_with_focused_ran(command: str, focused_ran: list[str] | None) -> str:
    guide_ids = [str(guide_id).strip() for guide_id in list(focused_ran or []) if str(guide_id).strip()]
    if not guide_ids:
        return command
    args = " ".join(f"--focused-ran {shlex.quote(guide_id)}" for guide_id in guide_ids)
    return f"{command} {args}"


def _command_with_workdir(command: str, *, workdir: Path) -> str:
    if workdir.resolve() == Path.cwd().resolve():
        return command
    return f"{command} --workdir {shlex.quote(str(workdir))}"


__all__ = (
    "copyable_dev_check_command",
    "dev_check_command",
    "dev_check_default_fast_command",
    "dev_check_final_pr_evidence_command",
    "dev_check_focused_command",
    "dev_check_list_command",
)
