from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora.agent_adapter_check_utils import adapter_unavailable_summary as _adapter_unavailable_summary
from loopora.agent_adapter_host_config import host_config_status as _host_config_status
from loopora.agent_adapter_managed_files import (
    managed_file_status as _managed_file_status,
    managed_status_paths as _managed_status_paths,
)
from loopora.agent_adapter_manifest import (
    manifest_relative_path as _manifest_relative_path,
    read_manifest as _read_manifest,
)
from loopora.agent_adapter_templates import managed_templates as _adapter_managed_templates


def not_implemented_adapter_status(kind: str, root: Path) -> dict[str, Any]:
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "implemented": False,
        "status": "not_implemented",
        "summary": _adapter_unavailable_summary(kind),
        "managed_files": [],
        "manifest_path": "",
        "error": "",
    }


def managed_adapter_status(kind: str, root: Path) -> dict[str, Any]:
    templates = _adapter_managed_templates(kind)
    manifest_payload, manifest_error = _read_manifest(kind, root)
    manifest_path = root / _manifest_relative_path(kind)
    managed_files = []
    if manifest_error:
        return {
            "adapter": kind,
            "label": _adapter_label(kind),
            "workdir": str(root),
            "implemented": True,
            "status": "error",
            "summary": f"Cannot read Loopora {_adapter_label(kind)} adapter manifest",
            "managed_files": [],
            "manifest_path": str(manifest_path),
            "error": manifest_error,
        }

    manifest_exists = isinstance(manifest_payload, dict)
    unmanaged_conflicts = []
    needs_update = False
    installed_count = 0
    paths = _managed_status_paths(kind, root, manifest_payload, manifest_exists=manifest_exists, templates=templates)
    managed_marker_found = False
    for relative_path in paths:
        expected = templates.get(relative_path, "")
        file_state = _managed_file_status(
            kind,
            root,
            relative_path,
            expected,
            manifest_context=(manifest_payload, manifest_exists),
        )
        file_payload = file_state["payload"]
        installed_count += int(file_state["current"])
        needs_update = needs_update or bool(file_state["needs_update"])
        managed_marker_found = managed_marker_found or bool(file_state["managed_marker"])
        if file_state["unmanaged_conflict"]:
            unmanaged_conflicts.append(relative_path)
        managed_files.append(file_payload)

    host_config_state = _host_config_status(kind, root, manifest_exists=manifest_exists)
    if host_config_state:
        managed_files.append(host_config_state["payload"])
        needs_update = needs_update or bool(host_config_state["needs_update"])
        if host_config_state["unmanaged_conflict"]:
            unmanaged_conflicts.append(host_config_state["payload"]["path"])

    if unmanaged_conflicts:
        status = "error"
        summary = f"{_adapter_label(kind)} adapter files exist but ownership is unclear"
        error = "unmanaged files: " + ", ".join(unmanaged_conflicts)
    elif manifest_exists and needs_update:
        status = "needs_update"
        summary = f"{_adapter_label(kind)} adapter is installed but needs update"
        error = ""
    elif manifest_exists and installed_count == len(templates):
        status = "installed"
        summary = f"{_adapter_label(kind)} adapter is installed"
        error = ""
    elif not manifest_exists and (installed_count == len(templates) or managed_marker_found):
        status = "needs_update"
        summary = f"{_adapter_label(kind)} adapter files exist but manifest is missing"
        error = ""
    else:
        status = "not_installed"
        summary = f"{_adapter_label(kind)} adapter is not installed"
        error = ""
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "implemented": True,
        "status": status,
        "summary": summary,
        "managed_files": managed_files,
        "manifest_path": str(manifest_path),
        "error": error,
    }
