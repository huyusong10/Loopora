from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


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
AdapterMessageOption = Annotated[
    str,
    typer.Option("--message", help="Short task summary for the Loop preview; required for Agent-first traceability."),
]
NoWebOption = Annotated[bool, typer.Option("--no-web", hidden=True, help="Skip local Web service startup.")]
CheckOption = Annotated[bool, typer.Option("--check", help="Check the Loopora Agent entry without installing or repairing files.")]
SourceOptionIdOption = Annotated[str, typer.Option("--source-option-id", help="Recoverable Loopora context option id selected by the user.")]
