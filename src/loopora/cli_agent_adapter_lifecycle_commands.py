from __future__ import annotations

from pathlib import Path

import typer

from loopora.cli_agent_adapter_output import (
    handle_adapter_install_conflict as _handle_adapter_install_conflict,
    is_adapter_install_conflict as _is_adapter_install_conflict,
    print_adapter_check_result as _print_adapter_check_result,
    print_adapter_mutation_result as _print_adapter_mutation_result,
)
from loopora.cli_shared import JsonOutputOption, handle_error
from loopora.agent_adapters import check_agent_adapter, install_agent_adapter, uninstall_agent_adapter
from loopora.service import LooporaError
from loopora.service_types import LooporaConflictError


from typing import Annotated


AdapterWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Project directory where the Coding Agent will work.",
    ),
]

ContextIdOption = Annotated[
    str,
    typer.Option("--context-id", help="Optional host session/thread identity. Defaults to Loopora, Codex, Claude Code, or OpenCode session env vars, then workdir."),
]

EntrySourceOption = Annotated[
    str,
    typer.Option("--entry-source", hidden=True, help="Internal marker for Loopora-managed Agent entry provenance."),
]

CompactJsonOutputOption = Annotated[
    bool,
    typer.Option(
        "--compact-json",
        help="Print Agent Native v3 summary JSON without the raw legacy payload.",
    ),
]

BundleFileOption = Annotated[
    Path | None,
    typer.Option(
        "--bundle-file",
        "--plan-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Candidate Loop plan file produced by the Coding Agent.",
    ),
]

ResultFileOption = Annotated[
    Path,
    typer.Option("--result-file", file_okay=True, dir_okay=False, help="JSON result produced by the host Agent for the claimed Loopora step."),
]

RunIdOption = Annotated[str, typer.Option("--run-id", help="Optional Loopora run id. Defaults to the run bound to the current host session/workdir.")]

StepIdOption = Annotated[str, typer.Option("--step-id", help="Loopora step id being submitted.")]

NextStepIdCompatOption = Annotated[
    str,
    typer.Option(
        "--step-id",
        help="Compatibility no-op: agent next always claims the run's active step and cannot select an arbitrary step.",
    ),
]

AdapterMessageOption = Annotated[
    str,
    typer.Option("--message", help="Task context for the Loop preview; required for Agent-first traceability."),
]

NoWebOption = Annotated[bool, typer.Option("--no-web", hidden=True, help="Skip local Web service startup.")]

CheckOption = Annotated[bool, typer.Option("--check", help="Check the Loopora Agent entry without installing or repairing files.")]

SourceOptionIdOption = Annotated[str, typer.Option("--source-option-id", help="Recoverable Loopora context option id selected by the user.")]


def register_agent_adapter_lifecycle_commands(init_app: typer.Typer, uninstall_app: typer.Typer) -> None:
    _register_init_commands(init_app)
    _register_uninstall_commands(uninstall_app)


def _register_init_commands(init_app: typer.Typer) -> None:
    @init_app.command("codex")
    def init_codex(workdir: AdapterWorkdirOption = Path(), *, check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Codex project entry for task-judgment first use.

        Then return to Codex with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("codex", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("claude")
    def init_claude(workdir: AdapterWorkdirOption = Path(), *, check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Claude Code project entry for task-judgment first use.

        Then return to Claude Code with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("claude", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("opencode")
    def init_opencode(workdir: AdapterWorkdirOption = Path(), *, check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
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
        result = install_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="installed", json_output=json_output)
    except LooporaConflictError as exc:
        if _is_adapter_install_conflict(exc):
            _handle_adapter_install_conflict(adapter, workdir=workdir, exc=exc, json_output=json_output)
        else:
            handle_error(exc, json_output=json_output)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def _check_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = check_agent_adapter(adapter, workdir=workdir)
        _print_adapter_check_result(result, json_output=json_output)
        if result.get("check_status") != "pass":
            raise typer.Exit(code=1)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def _register_uninstall_commands(uninstall_app: typer.Typer) -> None:
    @uninstall_app.command("codex")
    def uninstall_codex(workdir: AdapterWorkdirOption = Path(), *, json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Codex project entry."""
        _uninstall_adapter("codex", workdir=workdir, json_output=json_output)

    @uninstall_app.command("claude")
    def uninstall_claude(workdir: AdapterWorkdirOption = Path(), *, json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Claude Code project entry."""
        _uninstall_adapter("claude", workdir=workdir, json_output=json_output)

    @uninstall_app.command("opencode")
    def uninstall_opencode(workdir: AdapterWorkdirOption = Path(), *, json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed OpenCode project entry."""
        _uninstall_adapter("opencode", workdir=workdir, json_output=json_output)


def _uninstall_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = uninstall_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="uninstalled", json_output=json_output)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)


def register_agent_check_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("check")
    def agent_check(workdir: AdapterWorkdirOption = Path(), *, json_output: JsonOutputOption = False) -> None:
        """Check the Loopora-managed project entry for this Agent adapter."""
        _check_adapter(adapter, workdir=workdir, json_output=json_output)
