from __future__ import annotations

import typer

from loopora.cli_summary_helpers import clip as _clip


def print_agent_continuation(continuation: object) -> None:
    if not isinstance(continuation, dict) or continuation.get("active") is not True:
        return
    verdict = continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    previous_run_id = str(continuation.get("previous_run_id") or "").strip()
    if previous_run_id:
        typer.echo(f"continuation_previous_run: {previous_run_id}")
    status = str(verdict.get("status") or "").strip()
    if status:
        typer.echo(f"continuation_task_verdict: {status}")
    summary = str(verdict.get("summary") or "").strip()
    if summary:
        typer.echo(f"continuation_task_verdict_summary: {_clip(summary, 200)}")
    _print_continuation_coverage(coverage)
    _print_continuation_focus_items("blocking", continuation.get("focus_blocking"))
    _print_continuation_focus_items("unproven", continuation.get("focus_unproven"))
    _print_continuation_focus_items("weak", continuation.get("focus_weak"))
    _print_continuation_next_focus(continuation.get("next_focus"))


def _print_continuation_coverage(coverage: dict) -> None:
    missing = coverage.get("missing_check_count")
    covered = coverage.get("covered_check_count")
    if covered is not None or missing is not None:
        typer.echo(f"continuation_required_coverage: {covered or 0} covered / {missing or 0} missing")
    target_count = coverage.get("target_count")
    covered_targets = coverage.get("covered_target_count")
    weak_targets = coverage.get("weak_target_count")
    missing_targets = coverage.get("missing_target_count")
    blocked_targets = coverage.get("blocked_target_count")
    if target_count:
        target_bits = [f"{covered_targets or 0} covered"]
        if weak_targets:
            target_bits.append(f"{weak_targets} weak")
        if missing_targets:
            target_bits.append(f"{missing_targets} missing")
        if blocked_targets:
            target_bits.append(f"{blocked_targets} blocked")
        typer.echo(f"continuation_coverage_targets: {target_count} total ({' / '.join(target_bits)})")


def _print_continuation_next_focus(items: object) -> None:
    next_focus = [str(item).strip() for item in list(items or []) if str(item).strip()]
    if next_focus:
        typer.echo("continuation_next_focus:")
        for item in next_focus[:5]:
            typer.echo(f"- {item}")


def _print_continuation_focus_items(label: str, items: object) -> None:
    focus_items = [str(item).strip() for item in list(items or []) if str(item).strip()]
    if not focus_items:
        return
    typer.echo(f"continuation_{label}:")
    for item in focus_items[:4]:
        typer.echo(f"- {_clip(item, 180)}")
