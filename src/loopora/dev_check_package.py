from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from loopora.dev_check_package_contents import (
    forbidden_sdist_distribution_entries,
    forbidden_wheel_distribution_entries,
    missing_sdist_public_assets,
    missing_sdist_runtime_assets,
    missing_source_runtime_entry_files,
    missing_wheel_runtime_assets,
    public_sdist_asset_files,
    runtime_package_asset_files,
)
from loopora.dev_check_package_lifecycle import cleanup_generated_package_metadata
from loopora.dev_check_package_lifecycle import cleanup_package_build_output
from loopora.dev_check_package_lifecycle import package_build_lock
from loopora.dev_check_package_lifecycle import prepare_package_build_dir
from loopora.dev_check_package_metadata import missing_sdist_install_metadata
from loopora.dev_check_package_metadata import missing_wheel_install_metadata
from loopora.dev_check_package_metadata import project_metadata
from loopora.dev_check_package_metadata import project_public_positioning_errors
from loopora.dev_check_package_policy import PACKAGE_BUILD_OUTPUT_DIR
from loopora.dev_check_package_provenance import package_source_provenance_errors
from loopora.dev_check_types import DevCheckCommandResult
from loopora.service_types import LooporaError

PackageCommandRunner = Callable[[tuple[str, ...], Path], DevCheckCommandResult]


def run_package_build_step(
    root: Path,
    command: tuple[str, str, str, tuple[str, ...] | None],
    *,
    runner: PackageCommandRunner,
) -> DevCheckCommandResult:
    argv = command[3]
    if argv is None:
        raise LooporaError(f"missing executable command for dev check step: {command[0]}")
    try:
        with package_build_lock(root):
            try:
                prepare_package_build_dir(root)
                result = runner(argv, root)
                if result.returncode != 0:
                    return result
                artifact_result = _verify_package_artifacts(root, result)
                return _verify_installed_wheel_cli(root, artifact_result, runner=runner) if artifact_result.returncode == 0 else artifact_result
            finally:
                cleanup_generated_package_metadata(root)
                cleanup_package_build_output(root)
    except LooporaError as exc:
        return DevCheckCommandResult(returncode=1, stdout="", stderr=f"{exc}\n")


def _verify_package_artifacts(root: Path, build_result: DevCheckCommandResult) -> DevCheckCommandResult:
    package_dir = root / PACKAGE_BUILD_OUTPUT_DIR
    wheels = sorted(package_dir.glob("*.whl"))
    sdists = sorted(package_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        return _package_artifact_failure(
            build_result,
            [f"expected exactly one wheel and one sdist in {PACKAGE_BUILD_OUTPUT_DIR}, found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"],
        )

    runtime_assets = runtime_package_asset_files(root)
    public_sdist_assets = public_sdist_asset_files(root)
    project = project_metadata(root)
    missing = [
        *project_public_positioning_errors(project),
        *missing_source_runtime_entry_files(root),
        *missing_wheel_install_metadata(root, wheels[0]),
        *missing_wheel_runtime_assets(wheels[0], runtime_assets),
        *missing_sdist_install_metadata(root, sdists[0]),
        *missing_sdist_runtime_assets(sdists[0], runtime_assets),
        *missing_sdist_public_assets(sdists[0], public_sdist_assets),
        *forbidden_wheel_distribution_entries(wheels[0]),
        *forbidden_sdist_distribution_entries(sdists[0]),
        *package_source_provenance_errors(wheels[0], sdists[0]),
    ]
    if missing:
        return _package_artifact_failure(build_result, missing)
    verified_count = len(runtime_assets) + len(public_sdist_assets)
    stdout = f"{build_result.stdout.rstrip()}\nverified package contents: {verified_count} runtime/public asset(s) plus install metadata\n"
    return DevCheckCommandResult(returncode=0, stdout=stdout, stderr=build_result.stderr)


def _package_artifact_failure(build_result: DevCheckCommandResult, messages: list[str]) -> DevCheckCommandResult:
    details = "\n".join(f"- {message}" for message in messages[:20])
    if len(messages) > 20:
        details = f"{details}\n- ... {len(messages) - 20} more missing package asset(s)"
    stderr = f"{build_result.stderr.rstrip()}\npackage content verification failed:\n{details}\n"
    return DevCheckCommandResult(returncode=1, stdout=build_result.stdout, stderr=stderr)


def _verify_installed_wheel_cli(
    root: Path,
    artifact_result: DevCheckCommandResult,
    *,
    runner: PackageCommandRunner,
) -> DevCheckCommandResult:
    wheel = next((root / PACKAGE_BUILD_OUTPUT_DIR).glob("*.whl"))
    command = ("uv", "run", "--isolated", "--no-project", "--offline", "--with", str(wheel), "loopora", "--version")
    smoke_result = runner(command, root)
    stdout = "\n".join(part for part in (artifact_result.stdout.rstrip(), smoke_result.stdout.rstrip()) if part)
    if smoke_result.returncode != 0:
        stderr = "\n".join(
            part
            for part in (
                artifact_result.stderr.rstrip(),
                "installed wheel CLI smoke check failed: loopora --version",
                smoke_result.stderr.rstrip(),
            )
            if part
        )
        return DevCheckCommandResult(returncode=smoke_result.returncode, stdout=f"{stdout}\n", stderr=f"{stderr}\n")
    return DevCheckCommandResult(
        returncode=0,
        stdout=f"{stdout}\nverified installed wheel CLI: loopora --version\n",
        stderr=artifact_result.stderr,
    )
