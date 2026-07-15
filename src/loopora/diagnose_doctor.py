from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import shlex
import sys
from typing import Any

from loopora.agent_adapters import check_agent_adapter, prefix_loopora_command
from loopora.agent_native_adapter_contracts import AGENT_ADAPTER_KINDS
from loopora.web_request_context import _is_loopback_host

DOCTOR_SCHEMA_VERSION = 1
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8742


def build_doctor_report(
    *,
    workdir: Path | str,
    web_host: str = DEFAULT_WEB_HOST,
    web_port: int = DEFAULT_WEB_PORT,
) -> dict[str, Any]:
    root = Path(workdir).resolve()
    agent_entries = [_agent_entry_report(adapter, root) for adapter in AGENT_ADAPTER_KINDS]
    ready_entries = [entry for entry in agent_entries if entry["ready"]]
    attention_entries = [entry for entry in agent_entries if _entry_needs_attention(entry)]
    status = _overall_status(ready_entries=ready_entries, attention_entries=attention_entries)
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "status": status,
        "ready": bool(ready_entries),
        "workdir": str(root),
        "package": _package_report(),
        "web": _web_report(web_host, web_port),
        "agent_entries": agent_entries,
        "ready_adapter_count": len(ready_entries),
        "attention_adapter_count": len(attention_entries),
        "recommended_adapter": ready_entries[0]["adapter"] if ready_entries else "codex",
        "next_steps": _next_steps(root, ready_entries=ready_entries),
    }


def doctor_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": report.get("schema_version"),
        "status": report.get("status"),
        "ready": report.get("ready"),
        "workdir": report.get("workdir"),
        "ready_adapter_count": report.get("ready_adapter_count"),
        "attention_adapter_count": report.get("attention_adapter_count"),
        "recommended_adapter": report.get("recommended_adapter"),
        "web_origin": (report.get("web") if isinstance(report.get("web"), dict) else {}).get("origin"),
        "next_steps": report.get("next_steps"),
    }


def doctor_json_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {"diagnose_doctor_summary": doctor_summary(report), **report}


def _agent_entry_report(adapter: str, root: Path) -> dict[str, Any]:
    result = check_agent_adapter(adapter, workdir=root)
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    check_status = str(result.get("check_status") or "fail")
    install_state = str(recovery.get("state") or result.get("status") or "unknown")
    details_are_expected = recovery.get("details_are_expected") is True
    checks = [item for item in list(result.get("checks") or []) if isinstance(item, dict)]
    failed_checks = [
        {
            "name": str(item.get("name") or ""),
            "path": str(item.get("path") or ""),
            "message": str(item.get("message") or ""),
        }
        for item in checks
        if item.get("status") != "pass"
    ]
    entry = {
        "adapter": adapter,
        "label": str(result.get("label") or adapter),
        "ready": check_status == "pass",
        "check_status": check_status,
        "install_state": install_state,
        "summary": str(recovery.get("summary") or ""),
        "details_are_expected": details_are_expected,
        "commands": _agent_entry_commands(adapter, root, recovery=recovery),
        "next_action": _agent_entry_next_action(check_status=check_status, install_state=install_state),
    }
    if failed_checks and not details_are_expected:
        entry["failed_checks"] = failed_checks
    return entry


def _agent_entry_commands(adapter: str, root: Path, *, recovery: dict[str, Any]) -> dict[str, str]:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = prefix_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))}")
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = prefix_loopora_command(f"loopora init {adapter} --workdir {shlex.quote(str(root))} --check")
    agent_check_command = prefix_loopora_command(f"loopora agent {adapter} check --workdir {shlex.quote(str(root))}")
    return {
        "install": install_command,
        "install_check": check_command,
        "agent_check": agent_check_command,
    }


def _agent_entry_next_action(*, check_status: str, install_state: str) -> str:
    if check_status == "pass":
        return "return_to_agent"
    if install_state == "not_installed":
        return "install_agent_entry"
    return "inspect_or_repair_agent_entry"


def _entry_needs_attention(entry: dict[str, Any]) -> bool:
    if entry.get("ready") is True:
        return False
    return str(entry.get("install_state") or "") != "not_installed"


def _overall_status(*, ready_entries: list[dict[str, Any]], attention_entries: list[dict[str, Any]]) -> str:
    if ready_entries and attention_entries:
        return "ready_with_warnings"
    if ready_entries:
        return "ready"
    return "not_ready"


def _next_steps(root: Path, *, ready_entries: list[dict[str, Any]]) -> list[str]:
    if ready_entries:
        label = str(ready_entries[0].get("label") or ready_entries[0].get("adapter") or "Agent")
        return [
            f"Return to {label} in this project with the task goal, fake-done risk, and required evidence.",
            "Run /loopora-plan to prepare the Loop preview before starting work.",
            "Review the READY Loop preview, then run /loopora-run in the same Agent session.",
            "Use `loopora serve --host 127.0.0.1 --port 8742` to observe evidence, gaps, and verdicts in Web.",
        ]
    return [
        f"Install one Agent entry, for example: {prefix_loopora_command(f'loopora init codex --workdir {shlex.quote(str(root))}')}",
        "Refresh or restart that Agent if the new slash commands are not visible.",
        "Return to the Agent with the task goal, fake-done risk, and required evidence, then run /loopora-plan.",
    ]


def _package_report() -> dict[str, str]:
    try:
        package_version = version("loopora")
    except PackageNotFoundError:
        package_version = "unknown"
    return {
        "name": "loopora",
        "version": package_version,
        "python": platform.python_version(),
        "python_executable": sys.executable,
    }


def _web_report(host: str, port: int) -> dict[str, Any]:
    loopback = _is_loopback_host(host)
    return {
        "default": host == DEFAULT_WEB_HOST and port == DEFAULT_WEB_PORT,
        "host": host,
        "port": port,
        "origin": f"http://{host}:{port}",
        "loopback": loopback,
        "requires_token_when_non_loopback": True,
        "start_command": prefix_loopora_command(f"loopora serve --host {shlex.quote(host)} --port {port}"),
    }
