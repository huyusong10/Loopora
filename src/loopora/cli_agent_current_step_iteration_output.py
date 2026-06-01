from __future__ import annotations

import typer

from loopora.agent_native_coverage_summary import evidence_scope_items as _evidence_scope_items
from loopora.agent_native_guidance import actionable_blocking_item as _actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _actionable_next_action
from loopora.cli_summary_helpers import clip as _clip
from loopora.cli_summary_helpers import non_bool_int as _non_bool_int


def print_agent_iteration_context(next_step: dict) -> None:
    iteration = _non_bool_int(next_step.get("iter"))
    step_order = _non_bool_int(next_step.get("step_order"))
    if iteration is None:
        return
    typer.echo(f"next_iteration: {iteration}")
    if step_order is not None:
        typer.echo(f"next_step_order: {step_order}")
    if iteration > 0 and (step_order or 0) == 0:
        typer.echo("iteration_continuation: previous iteration completed without closing the run; address current coverage gaps in this next pass")
        _print_agent_iteration_repair(next_step.get("iteration_repair"))


def _print_agent_iteration_repair(repair: object) -> None:
    if not isinstance(repair, dict) or repair.get("active") is not True:
        return
    source_step = str(repair.get("source_step_id") or "").strip()
    source_role = str(repair.get("source_role") or "").strip()
    if source_step or source_role:
        source = source_step
        if source_role:
            source = f"{source_step} ({source_role})" if source_step else source_role
        typer.echo(f"iteration_repair_source: {source}")
    summary = str(repair.get("summary") or "").strip()
    if summary:
        typer.echo(f"iteration_repair_summary: {_clip(summary, 220)}")
    blocking_items = _evidence_scope_items(repair.get("blocking_items"))
    if blocking_items:
        typer.echo("iteration_repair_blocking_items:")
        for item in blocking_items[:5]:
            typer.echo(f"- {_clip(_actionable_blocking_item(item), 220)}")
    next_action = _actionable_next_action(
        str(repair.get("recommended_next_action") or "").strip(),
        [_actionable_blocking_item(item) for item in blocking_items],
    )
    if next_action:
        typer.echo(f"iteration_repair_next_action: {_clip(next_action, 220)}")
    evidence_refs = _evidence_scope_items(repair.get("evidence_refs"))
    if evidence_refs:
        typer.echo("iteration_repair_evidence_refs:")
        for item in evidence_refs[:5]:
            typer.echo(f"- {item}")
