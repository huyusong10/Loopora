from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from loopora.service_types import LooporaError

DEV_CHECK_SCHEMA_VERSION = 1
DEFAULT_FAST_PROFILE = "default-fast"
PACKAGE_BUILD_OUTPUT_DIR = Path("tmp/package-check")
GENERATED_PACKAGE_METADATA_DIRS = (Path("src/loopora.egg-info"),)

DEFAULT_FAST_COMMANDS = (
    ("dependency_sync", "Check locked dependency resolution", "uv sync --locked --dry-run", ("uv", "sync", "--locked", "--dry-run")),
    ("dependency_compatibility", "Check dependency compatibility", "uv pip check", ("uv", "pip", "check")),
    (
        "static_js_syntax",
        "Check static JavaScript syntax",
        "find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check",
        None,
    ),
    ("python_static_checks", "Run Python static checks", "uv run ruff check src/loopora tests", ("uv", "run", "ruff", "check", "src/loopora", "tests")),
    ("whitespace_safe_diff", "Check whitespace-safe diff", "git diff --check", ("git", "diff", "--check")),
    ("package_build", "Build package", "uv build --out-dir tmp/package-check", ("uv", "build", "--out-dir", "tmp/package-check")),
    ("contract_checks", "Run contract checks", "uv run pytest -q tests/checks/contracts", ("uv", "run", "pytest", "-q", "tests/checks/contracts")),
)


@dataclass(frozen=True)
class DevCheckCommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[tuple[str, ...], Path], DevCheckCommandResult]


def run_dev_check(
    *,
    workdir: Path | str,
    profile: str = DEFAULT_FAST_PROFILE,
    list_only: bool = False,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    root = Path(workdir).resolve()
    normalized_profile = str(profile or "").strip() or DEFAULT_FAST_PROFILE
    if normalized_profile != DEFAULT_FAST_PROFILE:
        raise LooporaError(f"unsupported dev check profile: {profile!r}. Expected: {DEFAULT_FAST_PROFILE}")
    steps = [_listed_step(command) for command in DEFAULT_FAST_COMMANDS]
    if list_only:
        return _report(root, profile=normalized_profile, status="listed", steps=steps)

    runner = command_runner or _run_subprocess
    executed_steps: list[dict[str, Any]] = []
    failed = False
    for command in DEFAULT_FAST_COMMANDS:
        if failed:
            skipped = _listed_step(command)
            skipped["status"] = "skipped"
            executed_steps.append(skipped)
            continue
        step = _run_step(root, command, runner=runner)
        executed_steps.append(step)
        failed = step["status"] != "pass"
    return _report(root, profile=normalized_profile, status="fail" if failed else "pass", steps=executed_steps)


def _run_step(root: Path, command: tuple[str, str, str, tuple[str, ...] | None], *, runner: CommandRunner) -> dict[str, Any]:
    step = _listed_step(command)
    started = time.monotonic()
    try:
        if step["id"] == "package_build":
            _prepare_package_build_dir(root)
        if step["id"] == "static_js_syntax":
            result = _run_static_js_check(root, runner=runner)
        else:
            argv = command[3]
            if argv is None:
                raise LooporaError(f"missing executable command for dev check step: {step['id']}")
            result = runner(argv, root)
    finally:
        if step["id"] == "package_build":
            _cleanup_generated_package_metadata(root)
    step["duration_seconds"] = round(time.monotonic() - started, 3)
    step["returncode"] = result.returncode
    step["status"] = "pass" if result.returncode == 0 else "fail"
    if result.stdout:
        step["stdout"] = _bounded_text(result.stdout)
    if result.stderr:
        step["stderr"] = _bounded_text(result.stderr)
    return step


def _run_static_js_check(root: Path, *, runner: CommandRunner) -> DevCheckCommandResult:
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


def _prepare_package_build_dir(root: Path) -> None:
    package_dir = root / PACKAGE_BUILD_OUTPUT_DIR
    shutil.rmtree(package_dir, ignore_errors=True)
    package_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_generated_package_metadata(root)


def _cleanup_generated_package_metadata(root: Path) -> None:
    for relative_path in GENERATED_PACKAGE_METADATA_DIRS:
        shutil.rmtree(root / relative_path, ignore_errors=True)


def _listed_step(command: tuple[str, str, str, tuple[str, ...] | None]) -> dict[str, Any]:
    return {
        "id": command[0],
        "label": command[1],
        "command": command[2],
        "status": "listed",
    }


def _report(root: Path, *, profile: str, status: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    failed_step = next((step for step in steps if step.get("status") == "fail"), None)
    return {
        "dev_check_summary": {
            "schema_version": DEV_CHECK_SCHEMA_VERSION,
            "profile": profile,
            "status": status,
            "ready": status in {"listed", "pass"},
            "workdir": str(root),
            "step_count": len(steps),
            "failed_step_id": failed_step.get("id") if failed_step else "",
        },
        "schema_version": DEV_CHECK_SCHEMA_VERSION,
        "profile": profile,
        "status": status,
        "ready": status in {"listed", "pass"},
        "workdir": str(root),
        "steps": steps,
    }


def _run_subprocess(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return DevCheckCommandResult(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)


def _bounded_text(text: str, *, limit: int = 4000) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return value[-limit:]
