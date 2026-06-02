from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.dev_reset import dev_reset_loopora_state

DevResetWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Project directory whose development Loopora state should be reset.",
    ),
]
DevResetYesOption = Annotated[
    bool,
    typer.Option("--yes", help="Actually delete the planned Loopora development state. Without this flag the command is a dry run."),
]

DEV_RESET_SUMMARY_SCHEMA_VERSION = 3


def register_dev_commands(dev_app: typer.Typer) -> None:
    @dev_app.command("reset")
    def reset(
        workdir: DevResetWorkdirOption = Path(),
        *,
        yes: DevResetYesOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Preview or reset incompatible v3 development state for one project."""
        try:
            result = dev_reset_loopora_state(workdir=workdir, apply=yes)
        except OSError as exc:
            handle_error(exc)
            return
        if json_output:
            echo_json(_dev_reset_json_payload(result))
            return
        _print_dev_reset_result(result)


def _dev_reset_json_payload(result: dict) -> dict:
    planned = [str(item) for item in list(result.get("planned") or []) if str(item).strip()]
    removed = [str(item) for item in list(result.get("removed") or []) if str(item).strip()]
    skipped = [str(item) for item in list(result.get("skipped") or []) if str(item).strip()]
    return {
        "dev_reset_summary": {
            "schema_version": DEV_RESET_SUMMARY_SCHEMA_VERSION,
            "workdir": str(result.get("workdir") or "").strip(),
            "dry_run": result.get("dry_run") is not False,
            "planned_count": len(planned),
            "removed_count": len(removed),
            "skipped_count": len(skipped),
            "state": "reset_preview" if result.get("dry_run") is not False else "reset_complete",
        },
        **result,
    }


def _print_dev_reset_result(result: dict) -> None:
    planned = [str(item) for item in list(result.get("planned") or []) if str(item).strip()]
    removed = [str(item) for item in list(result.get("removed") or []) if str(item).strip()]
    skipped = [str(item) for item in list(result.get("skipped") or []) if str(item).strip()]
    dry_run = result.get("dry_run") is not False
    typer.echo("Loopora v3 development reset preview" if dry_run else "Loopora v3 development reset complete")
    typer.echo(f"workdir: {result.get('workdir')}")
    typer.echo(f"dry_run: {str(dry_run).lower()}")
    typer.echo(f"planned_count: {len(planned)}")
    typer.echo(f"removed_count: {len(removed)}")
    if planned:
        typer.echo("planned:")
        for item in planned:
            typer.echo(f"- {item}")
    if removed:
        typer.echo("removed:")
        for item in removed:
            typer.echo(f"- {item}")
    if skipped:
        typer.echo("skipped_non_loopora_files:")
        for item in skipped:
            typer.echo(f"- {item}")
    if dry_run:
        typer.echo("next: rerun with --yes to delete the planned Loopora-owned development state")
