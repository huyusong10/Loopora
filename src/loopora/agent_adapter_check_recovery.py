from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora.agent_adapter_command_prefix import prefix_loopora_command


def adapter_check_recovery(kind: str, root: Path, *, status: dict[str, Any], check_status: str) -> dict[str, Any]:
    install_command = prefix_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))}")
    check_command = prefix_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))} --check")
    adapter_status = str(status.get("status") or "")
    if check_status == "pass":
        return {
            "state": "installed",
            "summary": f"{_adapter_label(kind)} Loopora entry is installed and passes static checks.",
            "install_command": "",
            "check_command": check_command,
            "details_are_expected": False,
        }
    if adapter_status == "not_installed":
        return {
            "state": "not_installed",
            "summary": (
                f"{_adapter_label(kind)} Loopora entry is not installed yet; missing managed files are expected before install."
            ),
            "install_command": install_command,
            "check_command": check_command,
            "details_are_expected": True,
        }
    return {
        "state": adapter_status or "needs_attention",
        "summary": f"{_adapter_label(kind)} Loopora entry needs attention; inspect failed checks before reinstalling.",
        "install_command": install_command,
        "check_command": check_command,
        "details_are_expected": False,
    }
