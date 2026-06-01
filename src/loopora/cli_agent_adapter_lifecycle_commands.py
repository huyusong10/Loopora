from __future__ import annotations

from pathlib import Path

import typer

from loopora.cli_agent_adapter_output import (
    handle_adapter_install_conflict as _handle_adapter_install_conflict,
    print_adapter_check_result as _print_adapter_check_result,
    print_adapter_mutation_result as _print_adapter_mutation_result,
)
from loopora.cli_agent_command_options import AdapterWorkdirOption, CheckOption
from loopora.cli_shared import JsonOutputOption, get_service, handle_error
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError


def register_agent_adapter_lifecycle_commands(init_app: typer.Typer, uninstall_app: typer.Typer) -> None:
    _register_init_commands(init_app)
    _register_uninstall_commands(uninstall_app)


def _register_init_commands(init_app: typer.Typer) -> None:
    @init_app.command("codex")
    def init_codex(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Codex project entry for task-judgment first use.

        Then return to Codex with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("codex", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("claude")
    def init_claude(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Claude Code project entry for task-judgment first use.

        Then return to Claude Code with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("claude", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("opencode")
    def init_opencode(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the OpenCode project entry for task-judgment first use.

        Then return to OpenCode with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("opencode", workdir=workdir, check=check, json_output=json_output)


def _install_adapter(adapter: str, *, workdir: Path, check: bool, json_output: bool) -> None:
    try:
        if check:
            _check_adapter(adapter, workdir=workdir, json_output=json_output)
            return
        result = get_service().install_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="installed", json_output=json_output)
    except LooporaConflictError as exc:
        _handle_adapter_install_conflict(adapter, workdir=workdir, exc=exc, json_output=json_output)
    except LooporaError as exc:
        handle_error(exc)


def _check_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = get_service().check_agent_adapter(adapter, workdir=workdir)
        _print_adapter_check_result(result, json_output=json_output)
        if result.get("check_status") != "pass":
            raise typer.Exit(code=1)
    except LooporaError as exc:
        handle_error(exc)


def _register_uninstall_commands(uninstall_app: typer.Typer) -> None:
    @uninstall_app.command("codex")
    def uninstall_codex(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Codex project entry."""
        _uninstall_adapter("codex", workdir=workdir, json_output=json_output)

    @uninstall_app.command("claude")
    def uninstall_claude(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Claude Code project entry."""
        _uninstall_adapter("claude", workdir=workdir, json_output=json_output)

    @uninstall_app.command("opencode")
    def uninstall_opencode(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed OpenCode project entry."""
        _uninstall_adapter("opencode", workdir=workdir, json_output=json_output)


def _uninstall_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = get_service().uninstall_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="uninstalled", json_output=json_output)
    except LooporaError as exc:
        handle_error(exc)


def register_agent_check_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("check")
    def agent_check(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Check the Loopora-managed project entry for this Agent adapter."""
        _check_adapter(adapter, workdir=workdir, json_output=json_output)
