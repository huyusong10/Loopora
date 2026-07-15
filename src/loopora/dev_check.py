from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import tomllib
from typing import Any
from zipfile import BadZipFile, ZipFile

from loopora.service_types import LooporaError

DEV_CHECK_SCHEMA_VERSION = 1
DEFAULT_FAST_PROFILE = "default-fast"
PACKAGE_BUILD_OUTPUT_DIR = Path("tmp/package-check")
GENERATED_PACKAGE_METADATA_DIRS = (Path("src/loopora.egg-info"),)
PACKAGE_RUNTIME_ASSET_ROOTS = (
    Path("templates"),
    Path("static"),
    Path("assets/alignment"),
    Path("assets/logo"),
    Path("assets/prompts"),
    Path("assets/spec_practices"),
    Path("assets/system_prompts"),
)
PACKAGE_PUBLIC_FILES = (
    Path("pyproject.toml"),
    Path("setup.py"),
    Path("MANIFEST.in"),
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("HUMAN-SHAPED-LOOP.md"),
    Path("HUMAN-SHAPED-LOOP.zh-CN.md"),
    Path("CONTRIBUTING.md"),
    Path("CODE_OF_CONDUCT.md"),
    Path("CHANGELOG.md"),
    Path("GOVERNANCE.md"),
    Path("SECURITY.md"),
    Path("SUPPORT.md"),
)
PACKAGE_PUBLIC_ASSET_ROOTS = (Path("assets/diagrams"), Path("design"))
PACKAGE_FORBIDDEN_PREFIXES = ("tests/", ".github/", "tmp/", ".loopora/", ".ralph/")
PACKAGE_ASSET_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".svg", ".yaml", ".yml"}
SOURCE_PROVENANCE_FILE = "_build_provenance.json"

DEFAULT_FAST_COMMANDS = (
    ("dependency_sync", "Check locked dependency resolution", "uv sync --locked --dry-run", ("uv", "sync", "--locked", "--dry-run")),
    ("dependency_compatibility", "Check dependency compatibility", "uv pip check", ("uv", "pip", "check")),
    (
        "static_js_syntax",
        "Check static JavaScript syntax",
        "find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check",
        None,
    ),
    (
        "python_static_checks",
        "Run Python static checks",
        "uv run ruff check src/loopora tests scripts",
        ("uv", "run", "ruff", "check", "src/loopora", "tests", "scripts"),
    ),
    (
        "complexity_budget",
        "Enforce the accepted repository complexity budget",
        "uv run python scripts/complexity_budget.py --enforce",
        ("uv", "run", "python", "scripts/complexity_budget.py", "--enforce"),
    ),
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
            argv = command[3]
            if argv is None:
                raise LooporaError("missing executable command for dev check step: package_build")
            build_result = runner(argv, root)
            result = build_result if build_result.returncode != 0 else _validate_package_build(root)
        elif step["id"] == "static_js_syntax":
            result = _run_static_js_check(root, runner=runner)
        else:
            argv = command[3]
            if argv is None:
                raise LooporaError(f"missing executable command for dev check step: {step['id']}")
            result = runner(argv, root)
    finally:
        if step["id"] == "package_build":
            _cleanup_package_build_output(root)
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


def _cleanup_package_build_output(root: Path) -> None:
    shutil.rmtree(root / PACKAGE_BUILD_OUTPUT_DIR, ignore_errors=True)


def _cleanup_generated_package_metadata(root: Path) -> None:
    for relative_path in GENERATED_PACKAGE_METADATA_DIRS:
        shutil.rmtree(root / relative_path, ignore_errors=True)


def _validate_package_build(root: Path) -> DevCheckCommandResult:  # noqa: C901 - one artifact audit keeps the distribution boundary cohesive.
    package_dir = root / PACKAGE_BUILD_OUTPUT_DIR
    wheels = sorted(package_dir.glob("*.whl"))
    sdists = sorted(package_dir.glob("*.tar.gz"))
    errors: list[str] = []
    if len(wheels) != 1:
        errors.append(f"package build expected one wheel, found {len(wheels)}")
    if len(sdists) != 1:
        errors.append(f"package build expected one sdist, found {len(sdists)}")
    if errors:
        return DevCheckCommandResult(returncode=1, stderr="\n".join(errors) + "\n")

    wheel_path = wheels[0]
    sdist_path = sdists[0]
    try:
        with ZipFile(wheel_path) as wheel:
            wheel_names = set(wheel.namelist())
            wheel_entries = {name: wheel.read(name) for name in wheel_names if name.endswith(("METADATA", "entry_points.txt", SOURCE_PROVENANCE_FILE))}
    except (BadZipFile, KeyError, OSError) as exc:
        return DevCheckCommandResult(returncode=1, stderr=f"wheel is not readable: {wheel_path.name}: {exc}\n")
    try:
        with tarfile.open(sdist_path) as sdist:
            sdist_names = set(sdist.getnames())
            provenance_member = next((member for member in sdist.getmembers() if member.name.endswith(f"/src/loopora/{SOURCE_PROVENANCE_FILE}")), None)
            provenance_stream = sdist.extractfile(provenance_member) if provenance_member is not None else None
            sdist_provenance = provenance_stream.read() if provenance_stream is not None else b""
    except (tarfile.TarError, OSError) as exc:
        return DevCheckCommandResult(returncode=1, stderr=f"sdist is not readable: {sdist_path.name}: {exc}\n")

    runtime_assets = _runtime_package_assets(root)
    public_assets = _public_package_assets(root)
    errors.extend(
        f"wheel missing runtime asset: loopora/{asset}"
        for asset in runtime_assets
        if f"loopora/{asset}" not in wheel_names
    )
    errors.extend(
        f"sdist missing runtime asset: src/loopora/{asset}"
        for asset in runtime_assets
        if not _sdist_contains(sdist_names, f"src/loopora/{asset}")
    )
    errors.extend(
        f"sdist missing public asset: {asset}"
        for asset in public_assets
        if not _sdist_contains(sdist_names, asset)
    )

    wheel_project_names = {name.removeprefix("loopora/") for name in wheel_names}
    sdist_project_names = {_sdist_project_name(name) for name in sdist_names}
    errors.extend(_forbidden_package_entries(wheel_project_names, artifact="wheel"))
    errors.extend(_forbidden_package_entries(sdist_project_names, artifact="sdist"))

    metadata_names = [name for name in wheel_names if name.endswith(".dist-info/METADATA")]
    entry_point_names = [name for name in wheel_names if name.endswith(".dist-info/entry_points.txt")]
    if len(metadata_names) != 1:
        errors.append(f"wheel expected one METADATA file, found {len(metadata_names)}")
    if len(entry_point_names) != 1:
        errors.append(f"wheel expected one entry_points.txt file, found {len(entry_point_names)}")
    if len(metadata_names) == 1:
        metadata = wheel_entries[metadata_names[0]].decode("utf-8", errors="replace")
        errors.extend(_wheel_metadata_errors(root, metadata))
    if len(entry_point_names) == 1:
        entry_points = wheel_entries[entry_point_names[0]].decode("utf-8", errors="replace")
        errors.extend(
            f"wheel missing console entry point: {line}"
            for line in ("[console_scripts]", "loopora = loopora.cli:app")
            if line not in entry_points
        )

    wheel_provenance = wheel_entries.get(f"loopora/{SOURCE_PROVENANCE_FILE}", b"")
    errors.extend(_provenance_errors(wheel_provenance, sdist_provenance))
    if errors:
        return DevCheckCommandResult(returncode=1, stderr="\n".join(errors) + "\n")
    return DevCheckCommandResult(
        returncode=0,
        stdout=(
            f"verified package artifacts: {wheel_path.name}, {sdist_path.name}\n"
            f"verified runtime assets: {len(runtime_assets)}; public sdist assets: {len(public_assets)}\n"
        ),
    )


def _runtime_package_assets(root: Path) -> list[str]:
    package_root = root / "src" / "loopora"
    assets = {"__main__.py"}
    for relative_root in PACKAGE_RUNTIME_ASSET_ROOTS:
        asset_root = package_root / relative_root
        if not asset_root.exists():
            continue
        assets.update(
            path.relative_to(package_root).as_posix()
            for path in asset_root.rglob("*")
            if path.is_file() and path.suffix.lower() in PACKAGE_ASSET_SUFFIXES
        )
    return sorted(assets)


def _public_package_assets(root: Path) -> list[str]:
    assets = {path.as_posix() for path in PACKAGE_PUBLIC_FILES if (root / path).is_file()}
    for relative_root in PACKAGE_PUBLIC_ASSET_ROOTS:
        asset_root = root / relative_root
        if not asset_root.exists():
            continue
        assets.update(path.relative_to(root).as_posix() for path in asset_root.rglob("*") if path.is_file())
    return sorted(assets)


def _sdist_contains(names: set[str], relative_path: str) -> bool:
    suffix = f"/{relative_path}"
    return any(name.endswith(suffix) for name in names)


def _sdist_project_name(name: str) -> str:
    normalized = name.strip().lstrip("/")
    return normalized.split("/", 1)[1] if "/" in normalized else ""


def _forbidden_package_entries(names: set[str], *, artifact: str) -> list[str]:
    return [
        f"{artifact} must not include local/test artifact: {name}"
        for name in sorted(names)
        if any(name == prefix.rstrip("/") or name.startswith(prefix) for prefix in PACKAGE_FORBIDDEN_PREFIXES)
    ]


def _wheel_metadata_errors(root: Path, metadata: str) -> list[str]:
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    required_lines = [
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project['description']}",
        f"Requires-Python: {project['requires-python']}",
        *(f"Project-URL: {label}, {url}" for label, url in sorted(project.get("urls", {}).items())),
        *(f"Requires-Dist: {dependency}" for dependency in project.get("dependencies", [])),
    ]
    errors = [f"wheel METADATA missing: {line}" for line in required_lines if line not in metadata]
    if "\nLicense:" in f"\n{metadata}" or "\nClassifier: License ::" in f"\n{metadata}":
        errors.append("wheel METADATA must not declare a license before maintainer approval")
    return errors


def _provenance_errors(wheel_payload: bytes, sdist_payload: bytes) -> list[str]:
    errors: list[str] = []
    payloads: list[dict[str, Any]] = []
    for artifact, raw_payload in (("wheel", wheel_payload), ("sdist", sdist_payload)):
        if not raw_payload:
            errors.append(f"{artifact} missing source provenance: {SOURCE_PROVENANCE_FILE}")
            continue
        try:
            payload = json.loads(raw_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{artifact} source provenance is unreadable: {exc}")
            continue
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "revision", "tree_status"}:
            errors.append(f"{artifact} source provenance must contain only schema_version, revision, and tree_status")
            continue
        payloads.append(payload)
    if len(payloads) == 2 and payloads[0] != payloads[1]:
        errors.append("wheel and sdist source provenance do not match")
    return errors


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
