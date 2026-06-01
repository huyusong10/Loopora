from __future__ import annotations

import typer

from loopora.agent_native_guidance import actionable_blocking_item, actionable_next_action
from loopora.cli_summary_helpers import clip as _clip
from loopora.cli_summary_helpers import clip_inline as _clip_inline


def _print_agent_submitted_step(submitted_step: object) -> None:
    if not isinstance(submitted_step, dict) or not submitted_step:
        return
    step_id = str(submitted_step.get("step_id") or "").strip()
    if step_id:
        typer.echo(f"submitted_step_id: {step_id}")
    status = str(submitted_step.get("status") or "").strip()
    if status:
        typer.echo(f"submitted_status: {status}")
    evidence_refs = [str(item) for item in list(submitted_step.get("evidence_refs") or []) if str(item).strip()]
    _print_agent_submitted_step_list("submitted_evidence_refs", evidence_refs, limit=8)
    _print_agent_submitted_coverage_results(submitted_step.get("coverage_results"))
    if _submitted_step_is_blocked(status):
        blocking_items = [
            actionable_blocking_item(str(item).strip()) for item in list(submitted_step.get("blocking_items") or []) if str(item).strip()
        ]
        _print_agent_submitted_step_list("submitted_blocking_items", blocking_items, limit=6, clip_items=True)
        next_action = actionable_next_action(str(submitted_step.get("recommended_next_action") or "").strip(), blocking_items)
        if next_action:
            typer.echo(f"submitted_next_action: {_clip(next_action, 220)}")
    handoff_path = str(submitted_step.get("handoff_absolute_path") or submitted_step.get("handoff_path") or "").strip()
    if handoff_path:
        typer.echo(f"submitted_handoff_path: {handoff_path}")
    _print_agent_submitted_native_trace(submitted_step)
    summary = str(submitted_step.get("summary") or "").strip()
    if summary:
        typer.echo(f"submitted_summary: {_clip(summary, 220)}")


def _print_agent_submitted_native_trace(submitted_step: dict[str, object]) -> None:
    host_dispatch = submitted_step.get("host_dispatch") if isinstance(submitted_step.get("host_dispatch"), dict) else {}
    native_trace = host_dispatch.get("native_trace") if isinstance(host_dispatch.get("native_trace"), dict) else {}
    if not native_trace:
        return
    trace_ref = str(native_trace.get("trace_ref") or native_trace.get("event_ref") or "").strip()
    tool_name = str(native_trace.get("tool_name") or "").strip()
    if tool_name:
        typer.echo(f"submitted_native_tool: {_clip(tool_name, 120)}")
    if trace_ref:
        typer.echo(f"submitted_native_trace: {_clip(trace_ref, 180)}")


def _submitted_step_is_blocked(status: str) -> bool:
    return status.strip().lower() in {"blocked", "failed", "errored", "rejected"}


def _print_agent_submitted_step_list(label: str, items: list[str], *, limit: int, clip_items: bool = False) -> None:
    if not items:
        return
    typer.echo(f"{label}:")
    for item in items[:limit]:
        typer.echo(f"- {_clip(item, 220) if clip_items else item}")
    if len(items) > limit:
        typer.echo(f"{label}_more: {len(items) - limit}")


def _print_agent_submitted_coverage_results(value: object) -> None:
    summaries = _submitted_coverage_result_summaries(value, limit=8)
    if not summaries:
        return
    counts = _coverage_result_counts(value)
    if counts:
        parts = [f"{status}={count}" for status, count in counts.items()]
        typer.echo(f"submitted_coverage_result_counts: {' '.join(parts)}")
    typer.echo("submitted_coverage_results:")
    for item in summaries:
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        refs = item.get("evidence_refs") if isinstance(item.get("evidence_refs"), list) else []
        refs_part = f" refs={','.join(str(ref) for ref in refs[:4])}" if refs else ""
        note = str(item.get("note") or "").strip()
        note_part = f": {_clip(note, 180)}" if note else ""
        typer.echo(f"- {target_id} {status}{refs_part}{note_part}")
    raw_items = [item for item in list(value or []) if isinstance(item, dict)] if isinstance(value, list) else []
    if len(raw_items) > len(summaries):
        typer.echo(f"submitted_coverage_results_more: {len(raw_items) - len(summaries)}")


def _submitted_coverage_result_summaries(value: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    summaries: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if not target_id or not status:
            continue
        summary: dict[str, object] = {"target_id": target_id, "status": status}
        evidence_refs = [str(ref).strip() for ref in list(item.get("evidence_refs") or []) if str(ref).strip()]
        if evidence_refs:
            summary["evidence_refs"] = evidence_refs[:6]
        note = str(item.get("note") or "").strip()
        if note:
            summary["note"] = _clip_inline(note, 180)
        summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def _coverage_result_counts(value: object) -> dict[str, int]:
    if not isinstance(value, list):
        return {}
    counts: dict[str, int] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip()
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts
