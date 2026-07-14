from __future__ import annotations

from pathlib import Path
import tarfile
import tomllib
from typing import Any
from zipfile import BadZipFile, ZipFile

from loopora.dev_check_package_policy import (
    PACKAGE_PUBLIC_AUTHOR,
    PACKAGE_PUBLIC_DESCRIPTION_TERMS,
    PACKAGE_PUBLIC_KEYWORDS,
    PACKAGE_PUBLIC_MAINTAINER,
    PACKAGE_PUBLIC_URLS,
)


def project_metadata(root: Path) -> dict[str, Any]:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def project_public_positioning_errors(project: dict[str, Any]) -> list[str]:
    description = str(project.get("description") or "").lower()
    errors = [f"project.description must keep public positioning term: {term}" for term in PACKAGE_PUBLIC_DESCRIPTION_TERMS if term not in description]
    raw_keywords = project.get("keywords", [])
    keywords = {str(keyword).lower() for keyword in raw_keywords} if isinstance(raw_keywords, list) else set()
    errors.extend(f"project.keywords must include public discovery keyword: {keyword}" for keyword in PACKAGE_PUBLIC_KEYWORDS if keyword not in keywords)
    if project.get("authors") != [{"name": PACKAGE_PUBLIC_AUTHOR}]:
        errors.append(f"project.authors must identify {PACKAGE_PUBLIC_AUTHOR}")
    if project.get("maintainers") != [{"name": PACKAGE_PUBLIC_MAINTAINER}]:
        errors.append(f"project.maintainers must identify {PACKAGE_PUBLIC_MAINTAINER}")
    urls = project.get("urls")
    if not isinstance(urls, dict):
        errors.append("project.urls must preserve public support, governance, security, and changelog links")
    else:
        errors.extend(f"project.urls must include public project URL: {label}" for label, url in PACKAGE_PUBLIC_URLS.items() if urls.get(label) != url)
    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list) or not all(isinstance(dependency, str) and dependency for dependency in dependencies):
        errors.append("project.dependencies must preserve runtime dependency metadata")
    return errors


def missing_wheel_install_metadata(root: Path, wheel_path: Path) -> list[str]:
    project = project_metadata(root)
    try:
        with ZipFile(wheel_path) as wheel:
            names = set(wheel.namelist())
            metadata_name = single_dist_info_name(names, "METADATA")
            entry_points_name = single_dist_info_name(names, "entry_points.txt")
            if not metadata_name or not entry_points_name:
                return [
                    *([] if metadata_name else ["wheel missing dist-info metadata: METADATA"]),
                    *([] if entry_points_name else ["wheel missing console entry points: entry_points.txt"]),
                ]
            metadata = wheel.read(metadata_name).decode("utf-8")
            entry_points = wheel.read(entry_points_name).decode("utf-8")
    except (BadZipFile, KeyError, UnicodeDecodeError) as exc:
        return [f"wheel install metadata is not readable: {wheel_path.name}: {exc}"]
    return [
        *missing_wheel_metadata_lines(project, metadata),
        *missing_entry_point_lines(entry_points, artifact="wheel"),
    ]


def single_dist_info_name(names: set[str], filename: str) -> str:
    matches = sorted(name for name in names if name.endswith(f".dist-info/{filename}"))
    return matches[0] if len(matches) == 1 else ""


def missing_wheel_metadata_lines(project: dict[str, Any], metadata: str) -> list[str]:
    required = [
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project['description']}",
        f"Author: {PACKAGE_PUBLIC_AUTHOR}",
        f"Maintainer: {PACKAGE_PUBLIC_MAINTAINER}",
        f"Requires-Python: {project['requires-python']}",
        f"Keywords: {','.join(str(keyword) for keyword in project['keywords'])}",
        "Description-Content-Type: text/markdown",
    ]
    required.extend(f"Classifier: {classifier}" for classifier in project["classifiers"])
    required.extend(f"Project-URL: {label}, {url}" for label, url in sorted(project["urls"].items()))
    required.extend(f"Requires-Dist: {dependency}" for dependency in project["dependencies"])
    missing = [f"wheel METADATA missing: {line}" for line in required if line not in metadata]
    if "\nLicense:" in f"\n{metadata}" or "\nClassifier: License ::" in f"\n{metadata}":
        missing.append("wheel METADATA must not declare a license before maintainer approval")
    return missing


def missing_entry_point_lines(entry_points: str, *, artifact: str) -> list[str]:
    required = ("[console_scripts]", "loopora = loopora.cli:app")
    return [f"{artifact} missing console script entry point: {line}" for line in required if line not in entry_points]


def missing_sdist_install_metadata(root: Path, sdist_path: Path) -> list[str]:
    project = project_metadata(root)
    text, error = sdist_file_text(sdist_path, "pyproject.toml")
    if error:
        return [error]
    try:
        sdist_project = tomllib.loads(text)["project"]
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        return [f"sdist pyproject metadata is not readable: {sdist_path.name}: {exc}"]
    missing = [
        f"sdist pyproject metadata mismatch: project.{key}"
        for key in ("name", "version", "description", "requires-python", "keywords", "classifiers", "dependencies", "authors", "maintainers", "urls")
        if sdist_project.get(key) != project.get(key)
    ]
    scripts = sdist_project.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("loopora") != "loopora.cli:app":
        missing.append("sdist pyproject missing console script: loopora = loopora.cli:app")
    if "license" in sdist_project or any(str(classifier).startswith("License ::") for classifier in sdist_project.get("classifiers", [])):
        missing.append("sdist pyproject must not declare a license before maintainer approval")
    return missing


def sdist_file_text(sdist_path: Path, relative_path: str) -> tuple[str, str]:
    try:
        with tarfile.open(sdist_path) as sdist:
            member = next((item for item in sdist.getmembers() if item.name.endswith(f"/{relative_path}")), None)
            if member is None:
                return "", f"sdist missing install metadata: {relative_path}"
            file_obj = sdist.extractfile(member)
            if file_obj is None:
                return "", f"sdist install metadata is not readable: {relative_path}"
            return file_obj.read().decode("utf-8"), ""
    except (tarfile.TarError, UnicodeDecodeError) as exc:
        return "", f"sdist install metadata is not readable: {sdist_path.name}: {exc}"
