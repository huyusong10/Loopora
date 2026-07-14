from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import sys
from typing import Any

from loopora.package_source_provenance import SOURCE_PROVENANCE_FILENAME, package_source_provenance


def package_identity_report() -> dict[str, Any]:
    try:
        package_version = version("loopora")
    except PackageNotFoundError:
        package_version = "unknown"
    source = _source_revision_report()
    return {
        "name": "loopora",
        "version": package_version,
        "source_revision": source["revision"],
        "source_tree_status": source["tree_status"],
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os": platform.system() or "unknown",
        "machine": platform.machine() or "unknown",
        "python_executable": sys.executable,
    }


def package_source_label(package: dict[str, Any]) -> str:
    revision = str(package.get("source_revision") or "").strip()
    if not revision or revision == "unknown":
        return ""
    status = str(package.get("source_tree_status") or "").strip()
    return f"source {revision}" + (f" {status}" if status and status != "unknown" else "")


def _source_revision_report() -> dict[str, str]:
    source_root = Path(__file__).resolve().parents[2]
    packaged_path = Path(__file__).with_name(SOURCE_PROVENANCE_FILENAME)
    return package_source_provenance(source_root=source_root, packaged_path=packaged_path)
