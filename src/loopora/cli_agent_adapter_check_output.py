from __future__ import annotations

import shlex

import typer

from loopora.agent_adapters import prefix_loopora_command
from loopora.agent_native_v3 import agent_v3_envelope, agent_v3_legacy_raw


def adapter_check_json_payload(result: dict) -> dict:
    summary = adapter_check_summary(result)
    return agent_v3_envelope(
        kind="agent_check",
        status=str(result.get("check_status") or "fail"),
        summary=summary,
        extras={
            "diagnostics": {"legacy_summary_key": "agent_check_summary"},
            "raw": agent_v3_legacy_raw(summary_key="agent_check_summary", summary=summary, payload=result),
        },
    )


def adapter_check_summary(result: dict) -> dict:
    recovery = result.get("check_recovery") if isinstance(result.get("check_recovery"), dict) else {}
    summary: dict[str, object] = {
        "schema_version": 3,
        "adapter": str(result.get("adapter") or "").strip(),
        "label": str(result.get("label") or "").strip(),
        "workdir": str(result.get("workdir") or "").strip(),
        "check_status": str(result.get("check_status") or "fail").strip(),
    }
    if recovery:
        summary["check_recovery"] = recovery
    surface = result.get("native_surface") if isinstance(result.get("native_surface"), dict) else {}
    if surface:
        summary["agent_surface"] = surface
        capabilities = surface.get("experience_capabilities") if isinstance(surface.get("experience_capabilities"), dict) else {}
        if capabilities:
            summary["experience_capabilities"] = capabilities
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def print_adapter_check_recovery_summary(recovery: dict) -> None:
    state = str(recovery.get("state") or "").strip()
    summary = str(recovery.get("summary") or "").strip()
    if state:
        typer.echo(f"install_state: {state}")
    if summary:
        typer.echo(f"summary: {summary}")


def print_adapter_check_recovery(result: dict, recovery: dict) -> None:
    install_command = str(recovery.get("install_command") or "").strip()
    if not install_command:
        install_command = prefix_loopora_command(
            f"loopora init {result.get('adapter')} --workdir {shlex.quote(str(result.get('workdir')))}"
        )
    check_command = str(recovery.get("check_command") or "").strip()
    if not check_command:
        check_command = f"{install_command} --check"
    typer.echo("recovery:")
    typer.echo(f"- Run: {install_command}")
    typer.echo(f"- Then verify: {check_command}")
    if recovery.get("state") != "not_installed":
        typer.echo("- If a file is unmanaged, inspect it before replacing or moving it.")
