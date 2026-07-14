from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_label as _adapter_label
from loopora.agent_adapter_command_prefix import copyable_loopora_command


def adapter_check_recovery(kind: str, root: Path, *, status: dict[str, Any], check_status: str) -> dict[str, Any]:
    install_command = copyable_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))}")
    check_command = copyable_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))} --check")
    doctor_command = copyable_loopora_command(f"loopora doctor --workdir {shlex.quote(str(root))}")
    web_start_command = copyable_loopora_command(
        f"loopora serve --open --workdir {shlex.quote(str(root))} --host 127.0.0.1 --port 8742"
    )
    adapter_status = str(status.get("status") or "")
    if check_status == "pass":
        return {
            "state": "installed",
            "summary": f"{_adapter_label(kind)} Loopora entry is installed and passes static checks.",
            "install_command": "",
            "check_command": check_command,
            "doctor_command": doctor_command,
            "web_start_command": web_start_command,
            "next_action_items": _installed_recovery_actions(
                doctor_command=doctor_command,
                web_start_command=web_start_command,
            ),
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
            "doctor_command": doctor_command,
            "web_start_command": web_start_command,
            "next_action_items": _not_installed_recovery_actions(
                install_command=install_command,
                check_command=check_command,
                doctor_command=doctor_command,
                web_start_command=web_start_command,
            ),
            "details_are_expected": True,
        }
    return {
        "state": adapter_status or "needs_attention",
        "summary": f"{_adapter_label(kind)} Loopora entry needs attention; inspect failed checks before reinstalling.",
        "install_command": install_command,
        "check_command": check_command,
        "doctor_command": doctor_command,
        "web_start_command": web_start_command,
        "next_action_items": _needs_attention_recovery_actions(
            install_command=install_command,
            check_command=check_command,
            doctor_command=doctor_command,
            web_start_command=web_start_command,
        ),
        "details_are_expected": False,
    }


def _not_installed_recovery_actions(
    *,
    install_command: str,
    check_command: str,
    doctor_command: str,
    web_start_command: str,
) -> list[dict[str, str]]:
    return [
        {"kind": "install_agent_entry", "command": install_command},
        {"kind": "verify_agent_entry", "command": check_command},
        *_installed_recovery_actions(doctor_command=doctor_command, web_start_command=web_start_command),
    ]


def _needs_attention_recovery_actions(
    *,
    install_command: str,
    check_command: str,
    doctor_command: str,
    web_start_command: str,
) -> list[dict[str, str]]:
    return [
        {"kind": "inspect_failed_checks"},
        {"kind": "install_agent_entry", "command": install_command},
        {"kind": "verify_agent_entry", "command": check_command},
        *_installed_recovery_actions(doctor_command=doctor_command, web_start_command=web_start_command),
    ]


def _installed_recovery_actions(
    *,
    doctor_command: str,
    web_start_command: str,
) -> list[dict[str, str]]:
    return [
        {"kind": "confirm_readiness", "command": doctor_command},
        {"kind": "return_to_agent"},
        {"kind": "confirm_agent_visibility"},
        {"kind": "run_loopora_plan", "command": "/loopora-plan"},
        {"kind": "review_ready_loop_preview"},
        {"kind": "run_loopora_run", "command": "/loopora-run"},
        {"kind": "start_web", "command": web_start_command},
    ]
