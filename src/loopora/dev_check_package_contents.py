from __future__ import annotations

from pathlib import Path
import tarfile
from zipfile import BadZipFile, ZipFile

from loopora.dev_check_package_policy import (
    PACKAGE_FORBIDDEN_DISTRIBUTION_PREFIXES,
    PACKAGE_RUNTIME_ASSET_ROOTS,
    PACKAGE_RUNTIME_ENTRY_FILES,
    PACKAGE_SDIST_PUBLIC_ASSET_ROOTS,
    PACKAGE_SDIST_PUBLIC_FILES,
)


def runtime_package_asset_files(root: Path) -> list[str]:
    package_root = root / "src" / "loopora"
    assets: set[str] = set()
    assets.update(path.as_posix() for path in PACKAGE_RUNTIME_ENTRY_FILES)
    for asset_root in PACKAGE_RUNTIME_ASSET_ROOTS:
        source_root = package_root / asset_root
        if source_root.exists():
            assets.update(path.relative_to(package_root).as_posix() for path in source_root.rglob("*") if path.is_file())
    return sorted(assets)


def missing_source_runtime_entry_files(root: Path) -> list[str]:
    package_root = root / "src" / "loopora"
    return [f"source missing runtime entry: src/loopora/{path.as_posix()}" for path in PACKAGE_RUNTIME_ENTRY_FILES if not (package_root / path).is_file()]


def public_sdist_asset_files(root: Path) -> list[str]:
    assets = {path.as_posix() for path in PACKAGE_SDIST_PUBLIC_FILES if (root / path).is_file()}
    for asset_root in PACKAGE_SDIST_PUBLIC_ASSET_ROOTS:
        source_root = root / asset_root
        if source_root.exists():
            assets.update(path.relative_to(root).as_posix() for path in source_root.rglob("*") if path.is_file())
    return sorted(assets)


def missing_wheel_runtime_assets(wheel_path: Path, runtime_assets: list[str]) -> list[str]:
    try:
        with ZipFile(wheel_path) as wheel:
            names = set(wheel.namelist())
    except BadZipFile as exc:
        return [f"wheel is not readable: {wheel_path.name}: {exc}"]
    return [f"wheel missing runtime asset: loopora/{asset}" for asset in runtime_assets if f"loopora/{asset}" not in names]


def missing_sdist_runtime_assets(sdist_path: Path, runtime_assets: list[str]) -> list[str]:
    names_or_error = sdist_names(sdist_path)
    if isinstance(names_or_error, str):
        return [names_or_error]
    names = names_or_error
    return [f"sdist missing runtime asset: src/loopora/{asset}" for asset in runtime_assets if not sdist_contains(names, f"src/loopora/{asset}")]


def missing_sdist_public_assets(sdist_path: Path, public_assets: list[str]) -> list[str]:
    names_or_error = sdist_names(sdist_path)
    if isinstance(names_or_error, str):
        return [names_or_error]
    names = names_or_error
    return [f"sdist missing public asset: {asset}" for asset in public_assets if not sdist_contains(names, asset)]


def forbidden_wheel_distribution_entries(wheel_path: Path) -> list[str]:
    try:
        with ZipFile(wheel_path) as wheel:
            names = set(wheel.namelist())
    except BadZipFile as exc:
        return [f"wheel is not readable: {wheel_path.name}: {exc}"]
    return forbidden_distribution_entry_errors(names, artifact="wheel")


def forbidden_sdist_distribution_entries(sdist_path: Path) -> list[str]:
    names_or_error = sdist_names(sdist_path)
    if isinstance(names_or_error, str):
        return [names_or_error]
    names = {sdist_project_relative_name(name) for name in names_or_error}
    return forbidden_distribution_entry_errors(names, artifact="sdist")


def forbidden_distribution_entry_errors(names: set[str], *, artifact: str) -> list[str]:
    return [f"{artifact} must not include local/test artifact: {name}" for name in sorted(names) if distribution_entry_is_forbidden(name)]


def distribution_entry_is_forbidden(name: str) -> bool:
    normalized = name.strip().lstrip("/")
    if not normalized:
        return False
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in PACKAGE_FORBIDDEN_DISTRIBUTION_PREFIXES)


def sdist_project_relative_name(name: str) -> str:
    normalized = name.strip().lstrip("/")
    if "/" not in normalized:
        return ""
    return normalized.split("/", 1)[1]


def sdist_names(sdist_path: Path) -> set[str] | str:
    try:
        with tarfile.open(sdist_path) as sdist:
            return set(sdist.getnames())
    except tarfile.TarError as exc:
        return f"sdist is not readable: {sdist_path.name}: {exc}"


def sdist_contains(names: set[str], relative_path: str) -> bool:
    suffix = f"/{relative_path}"
    return any(name.endswith(suffix) for name in names)
