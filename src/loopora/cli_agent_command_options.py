from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click
import typer


AdapterGroupWorkdirOption = Annotated[
    Path | None,
    typer.Option(
        "--workdir",
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Project directory to carry into this command group before choosing a subcommand.",
    ),
]
AdapterEntryWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Project directory where the Coding Agent will work.",
    ),
]
AdapterRuntimeWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=False,
        file_okay=True,
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
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Candidate Loop plan file produced by the Coding Agent.",
    ),
]
ResultFileOption = Annotated[
    Path | None,
    typer.Option("--result-file", file_okay=True, dir_okay=True, help="JSON result produced by the host Agent for the claimed Loopora step."),
]
AttestRoleDispatchOption = Annotated[
    bool,
    typer.Option(
        "--attest-role-dispatch",
        help=(
            "Attest that this host invoked the active target role agent and that --result-file contains "
            "that role's structured output."
        ),
    ),
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
    typer.Option("--message", help="Task context for the Loop preview; required for Agent-native traceability."),
]
NoWebOption = Annotated[bool, typer.Option("--no-web", hidden=True, help="Skip local Web service startup.")]
CheckOption = Annotated[bool, typer.Option("--check", help="Check the Loopora Agent entry without installing or repairing files.")]
SourceOptionIdOption = Annotated[str, typer.Option("--source-option-id", help="Recoverable Loopora context option id selected by the user.")]


def effective_adapter_workdir(ctx: typer.Context, workdir: Path) -> Path:
    if ctx.get_parameter_source("workdir") != click.core.ParameterSource.DEFAULT:
        return workdir
    parent = getattr(ctx, "parent", None)
    while parent is not None:
        parent_workdir = (getattr(parent, "params", {}) or {}).get("workdir")
        if parent_workdir is not None:
            return parent_workdir
        parent = getattr(parent, "parent", None)
    return workdir
