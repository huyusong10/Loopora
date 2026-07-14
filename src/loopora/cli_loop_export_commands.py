from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_shared import JsonOutputOption, echo_json, get_service, handle_error
from loopora.run_evidence_package import write_run_evidence_package
from loopora.service_types import LooporaError

LOOPS_EXPORT_RUN_HELP_EPILOG = (
    "Export-run creates a curated ZIP for reviewing one saved Run's contract, iteration summary, evidence ledger, "
    "coverage, manifest, and task verdict. It replaces local absolute paths and omits workspace files, prompts, raw "
    "model output, provider transcripts, events, and logs. The ZIP still contains private task content: review every "
    "file before sharing. It is not a public-safe support bundle, project backup, full transcript, or independent "
    "proof that the task passed. Existing output is never replaced unless --force is set."
)
RunEvidenceOutputOption = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="ZIP output path; defaults to the current directory."),
]
RunEvidenceForceOption = Annotated[
    bool,
    typer.Option("--force", help="Replace an existing output file."),
]


def register_loop_export_command(loops_app: typer.Typer) -> None:
    @loops_app.command("export-run", epilog=rewrite_loopora_help_commands(LOOPS_EXPORT_RUN_HELP_EPILOG))
    def export_run(
        run_id: str | None = typer.Argument(None, help="Run ID."),
        output: RunEvidenceOutputOption = None,
        *,
        force: RunEvidenceForceOption = False,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Export a private, review-ready Run evidence package."""
        run_id_value = str(run_id or "").strip()
        if not run_id_value:
            typer.echo("Choose a saved Run before exporting evidence.")
            typer.echo("List saved work: loopora loops list")
            typer.echo("Retry: loopora loops export-run <run-id>")
            raise typer.Exit(code=1)
        try:
            package = get_service().build_run_evidence_package(run_id_value)
            target = output if output is not None else Path.cwd() / package.filename
            written = write_run_evidence_package(target, package, overwrite=force)
            if json_output:
                echo_json(
                    {
                        "status": "exported",
                        "run_id": run_id_value,
                        "path": str(written),
                        "public_safe": False,
                        "content_scope": package.manifest["content_scope"],
                        "included_file_count": len(package.manifest["files"]),
                    }
                )
                return
            typer.echo(f"Evidence package: {written}")
            typer.echo("Scope: private task content; review every file before sharing.")
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)
