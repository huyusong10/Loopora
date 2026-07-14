from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from loopora.agent_adapter_check_utils import adapter_label
from loopora.workdir_inputs import workdir_path_state


def doctor_workdir_state(root: Path) -> dict[str, Any]:
    state = workdir_path_state(root)
    status = str(state.get("status") or "")
    workdir = str(state.get("workdir") or root)
    if status == "required":
        return {
            "status": "required",
            "workdir": workdir,
            "exists": False,
            "is_directory": False,
            "usable_for_agent_entries": False,
            "needs_attention": True,
            "summary": "Target project directory is required; choose a project directory before installing same-Agent project entries.",
            "error": "workdir is required",
            "commands": {},
        }
    if status == "unavailable":
        return {
            "status": "unavailable",
            "workdir": workdir,
            "exists": False,
            "is_directory": False,
            "usable_for_agent_entries": False,
            "needs_attention": True,
            "summary": "Target project directory cannot be inspected; choose a readable project directory before installing same-Agent project entries.",
            "error": "workdir could not be inspected",
            "commands": {},
        }
    if status == "missing":
        return {
            "status": "missing",
            "workdir": workdir,
            "exists": False,
            "is_directory": False,
            "usable_for_agent_entries": False,
            "needs_attention": True,
            "summary": "Target project directory does not exist yet; create it before installing same-Agent project entries.",
            "commands": {"create": f"mkdir -p {shlex.quote(workdir)}"},
        }
    if status == "not_directory":
        return {
            "status": "not_directory",
            "workdir": workdir,
            "exists": True,
            "is_directory": False,
            "usable_for_agent_entries": False,
            "needs_attention": True,
            "summary": "Configured workdir exists but is not a directory; choose a project directory path.",
            "commands": {},
        }
    return {
        "status": "ready",
        "workdir": workdir,
        "exists": True,
        "is_directory": True,
        "usable_for_agent_entries": True,
        "needs_attention": False,
        "summary": "",
        "commands": {},
    }


def target_required_doctor_workdir_state() -> dict[str, Any]:
    return {
        "status": "required",
        "workdir": "",
        "exists": False,
        "is_directory": False,
        "usable_for_agent_entries": False,
        "needs_attention": True,
        "summary": "Target project directory is required; choose a project directory before checking readiness.",
        "error": "workdir is required",
        "commands": {},
    }


def agent_entry_blocked_by_workdir(adapter: str, *, workdir_state: dict[str, Any]) -> dict[str, Any]:
    summary = str(workdir_state.get("summary") or "").strip()
    return {
        "adapter": adapter,
        "label": adapter_label(adapter),
        "ready": False,
        "check_status": "fail",
        "install_state": "blocked_by_workdir",
        "summary": summary,
        "details_are_expected": True,
        "commands": {},
        "next_action": "create_workdir" if workdir_state.get("status") == "missing" else "choose_workdir",
    }
