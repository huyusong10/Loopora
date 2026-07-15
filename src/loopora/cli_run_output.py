from __future__ import annotations

import typer

from loopora.cli_run_contract_output import print_run_contract_summary as print_run_contract_summary
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run


from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES

TASK_VERDICT_BUCKET_KEYS = ("proven", "weak", "unproven", "blocking", "residual_risk")

def print_task_verdict(task_verdict: object) -> None:
    if not isinstance(task_verdict, dict) or not task_verdict:
        typer.echo("task_verdict: not_evaluated")
        return
    status = str(task_verdict.get("status") or "not_evaluated")
    typer.echo(f"task_verdict: {status}")
    if task_verdict.get("source"):
        typer.echo(f"task_verdict_source: {task_verdict['source']}")
    if task_verdict.get("summary"):
        typer.echo(f"task_verdict_summary: {task_verdict['summary']}")
    buckets = task_verdict.get("buckets") if isinstance(task_verdict.get("buckets"), dict) else {}
    if buckets:
        counts = _task_verdict_bucket_counts(buckets)
        bucket_counts = [f"{bucket} {counts[bucket]}" for bucket in TASK_VERDICT_BUCKET_KEYS]
        typer.echo(f"task_verdict_buckets: {' / '.join(bucket_counts)}")
        _print_task_verdict_pass_basis(status, buckets, counts)

def _task_verdict_bucket_counts(buckets: dict) -> dict[str, int]:
    return {bucket: len(buckets.get(bucket) or []) for bucket in TASK_VERDICT_BUCKET_KEYS}

def _print_task_verdict_pass_basis(status: str, buckets: dict, counts: dict[str, int]) -> None:
    if status not in PASSING_TASK_VERDICT_STATUSES:
        return
    proven_required, total_required, open_required = _required_bucket_counts(buckets)
    if total_required:
        basis_bits = [f"{proven_required}/{total_required} required targets proven"]
        if counts["blocking"] == 0:
            basis_bits.append("blocking 0")
        else:
            basis_bits.append(f"blocking {counts['blocking']}")
        if open_required:
            basis_bits.append(f"{open_required} required open")
        typer.echo(f"task_verdict_required_basis: {'; '.join(basis_bits)}")
    if counts["blocking"] == 0 and open_required == 0 and any(counts[bucket] for bucket in ("weak", "unproven", "residual_risk")):
        typer.echo(
            "task_verdict_bucket_note: passing verdict kept non-blocking weak/unproven/residual buckets "
            "for audit or accepted follow-up; required coverage and GateKeeper support still passed"
        )

def _required_bucket_counts(buckets: dict) -> tuple[int, int, int]:
    proven_required = _required_item_count(buckets.get("proven"))
    open_required = sum(_required_item_count(buckets.get(bucket)) for bucket in ("weak", "unproven", "blocking"))
    return proven_required, proven_required + open_required, open_required

def _required_item_count(items: object) -> int:
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict) and item.get("required") is True)


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
