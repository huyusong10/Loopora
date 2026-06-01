from __future__ import annotations

import typer

from loopora.cli_run_contract_output import print_run_contract_summary as print_run_contract_summary
from loopora.cli_task_verdict_output import print_task_verdict as print_task_verdict
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run


def print_loop_created(loop: dict) -> None:
    typer.echo(f"loop: {loop['id']}")
    if loop.get("name"):
        typer.echo(f"name: {loop['name']}")
    if loop.get("workdir"):
        typer.echo(f"workdir: {loop['workdir']}")


def print_run_result(result: dict) -> None:
    from loopora.cli_common import echo_json

    typer.echo(f"run: {result['id']}")
    typer.echo(f"run_status: {run_status_from_run(result)}")
    typer.echo(f"run_dir: {result['runs_dir']}")
    print_run_contract_summary(result)
    print_task_verdict(task_verdict_from_run(result))
    if result.get("last_verdict_json"):
        typer.echo("raw_last_verdict_json:")
        echo_json(result["last_verdict_json"])
