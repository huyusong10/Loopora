from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shlex
import subprocess
import time
from typing import Any

from loopora.dev_check_focus import listed_focused_step
from loopora.dev_check_package import run_package_build_step
from loopora.dev_check_types import DevCheckCommandResult
from loopora.service_types import LooporaError


CommandRunner = Callable[[tuple[str, ...], Path], DevCheckCommandResult]
ProgressReporter = Callable[[dict[str, Any]], None]
DefaultFastCommand = tuple[str, str, str, tuple[str, ...] | None]


def run_default_step(
    root: Path,
    command: DefaultFastCommand,
    *,
    runner: CommandRunner,
    progress_reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    step = listed_step(command)
    emit_dev_check_progress(progress_reporter, event="step_started", step=step)
    started = time.monotonic()
    if step["id"] == "package_build":
        result = run_package_build_step(root, command, runner=runner)
    else:
        if step["id"] == "static_js_syntax":
            result = run_static_js_check(root, runner=runner)
        else:
            argv = command[3]
            if argv is None:
                raise LooporaError(f"missing executable command for dev check step: {step['id']}")
            result = runner(argv, root)
    _apply_command_result(step, result, started=started)
    emit_dev_check_progress(progress_reporter, event="step_finished", step=step)
    return step


def run_static_js_check(root: Path, *, runner: CommandRunner) -> DevCheckCommandResult:
    js_files = sorted((root / "src" / "loopora" / "static").glob("**/*.js"))
    if not js_files:
        return DevCheckCommandResult(returncode=0, stdout="No static JavaScript files found.\n")
    output: list[str] = []
    for js_file in js_files:
        result = runner(("node", "--check", str(js_file.relative_to(root))), root)
        if result.returncode != 0:
            return DevCheckCommandResult(
                returncode=result.returncode,
                stdout="\n".join([*output, result.stdout]).strip() + "\n",
                stderr=result.stderr,
            )
        output.append(result.stdout.strip() or f"ok: {js_file.relative_to(root)}")
    return DevCheckCommandResult(returncode=0, stdout="\n".join(output).strip() + "\n")


def run_focused_step(
    root: Path,
    guide: dict[str, Any],
    *,
    runner: CommandRunner,
    progress_reporter: ProgressReporter | None = None,
) -> dict[str, Any]:
    step = listed_focused_step(guide)
    emit_dev_check_progress(progress_reporter, event="step_started", step=step)
    started = time.monotonic()
    argv = tuple(shlex.split(str(guide.get("command") or "")))
    if not argv:
        raise LooporaError(f"missing executable command for focused check guide: {guide.get('id')}")
    result = runner(argv, root)
    _apply_command_result(step, result, started=started)
    emit_dev_check_progress(progress_reporter, event="step_finished", step=step)
    return step


def emit_dev_check_progress(progress_reporter: ProgressReporter | None, *, event: str, step: dict[str, Any]) -> None:
    if progress_reporter is None:
        return
    progress_reporter(
        {
            "event": event,
            "id": str(step.get("id") or ""),
            "label": str(step.get("label") or ""),
            "command": str(step.get("command") or ""),
            "status": str(step.get("status") or ""),
            "duration_seconds": step.get("duration_seconds"),
            "returncode": step.get("returncode"),
        }
    )


def listed_step(command: DefaultFastCommand) -> dict[str, Any]:
    return {
        "id": command[0],
        "label": command[1],
        "command": command[2],
        "status": "listed",
    }


def run_subprocess(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return DevCheckCommandResult(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _apply_command_result(step: dict[str, Any], result: DevCheckCommandResult, *, started: float) -> None:
    step["duration_seconds"] = round(time.monotonic() - started, 3)
    step["returncode"] = result.returncode
    step["status"] = "pass" if result.returncode == 0 else "fail"
    if result.stdout:
        step["stdout"] = _bounded_text(result.stdout)
    if result.stderr:
        step["stderr"] = _bounded_text(result.stderr)


def _bounded_text(text: str, *, limit: int = 4000) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return value[-limit:]
