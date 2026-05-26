from __future__ import annotations

import typer


def print_agent_submit_repair_plain(result: dict) -> None:
    _print_agent_submit_repair_header(result)
    _print_agent_submit_repair_context(result)
    _print_agent_submit_auto_repair_context(result)
    _print_agent_submit_repair_focus(result)
    typer.echo(f"next_repair_step: {result.get('next_repair_step')}", err=True)
    if result.get("schema_lookup"):
        typer.echo(f"schema_lookup: {result.get('schema_lookup')}", err=True)


def _print_agent_submit_repair_header(result: dict) -> None:
    typer.echo("submit_repair: result JSON needs repair before this Loopora step can advance", err=True)
    typer.echo(f"result_file_to_repair: {result.get('result_file_to_repair')}", err=True)
    for key in (
        "active_step_id",
        "active_role",
        "active_target_agent",
        "active_context_path",
        "active_result_template",
        "active_result_file_to_write",
        "result_outbox_dir",
    ):
        value = result.get(key)
        if value:
            typer.echo(f"{key}: {value}", err=True)
    _print_agent_submit_submitted_dispatch(result)


def _print_agent_submit_repair_focus(result: dict) -> None:
    focus = [str(item) for item in list(result.get("repair_focus") or []) if str(item).strip()]
    if not focus:
        return
    typer.echo("repair_focus:", err=True)
    for item in focus:
        typer.echo(f"- {item}", err=True)


def _print_agent_submit_repair_context(result: dict) -> None:
    known_ids = [str(item).strip() for item in list(result.get("active_known_evidence_ids") or []) if str(item).strip()]
    if known_ids:
        _print_agent_submit_repair_plain_list("active_known_evidence_ids", known_ids, limit=8)
    refs = result.get("active_known_evidence_refs")
    if isinstance(refs, list) and refs:
        _print_agent_submit_repair_known_evidence_refs(refs)
    target_ids = [str(item).strip() for item in list(result.get("active_coverage_target_ids") or []) if str(item).strip()]
    if target_ids:
        _print_agent_submit_repair_plain_list("active_coverage_target_ids", target_ids, limit=16)


def _print_agent_submit_auto_repair_context(result: dict) -> None:
    if result.get("auto_repair_attempted") is not True:
        return
    kind = str(result.get("core_blocker_kind") or "other_core_validation").strip()
    actions = [str(item).strip() for item in list(result.get("auto_repair_actions") or []) if str(item).strip()]
    action_text = f" ({', '.join(actions[:4])})" if actions else ""
    typer.echo(
        "auto_repair: submitted result format repaired before submit"
        f"{action_text}; Core still blocked {kind}",
        err=True,
    )


def _print_agent_submit_repair_plain_list(label: str, items: list[str], *, limit: int) -> None:
    displayed = items[:limit]
    typer.echo(f"{label}:", err=True)
    for item in displayed:
        typer.echo(f"- {item}", err=True)
    if len(items) > len(displayed):
        typer.echo(f"{label}_more: {len(items) - len(displayed)}", err=True)


def _print_agent_submit_repair_known_evidence_refs(refs: list[object]) -> None:
    summaries = [item for item in refs if isinstance(item, dict)]
    if not summaries:
        return
    typer.echo("active_known_evidence_refs:", err=True)
    for item in summaries[:5]:
        parts = [str(item.get("id") or "").strip()]
        result = str(item.get("result") or "").strip()
        if result:
            parts.append(f"result={result}")
        support = str(item.get("gatekeeper_support") or "").strip()
        if support:
            parts.append(f"support={support}")
        reason = str(item.get("gatekeeper_support_reason") or "").strip()
        if reason:
            parts.append(f"reason={reason}")
        typer.echo(f"- {' '.join(part for part in parts if part)}", err=True)
        claim = str(item.get("claim") or "").strip()
        if claim:
            typer.echo(f"  claim: {claim}", err=True)
        coverage_targets = item.get("coverage_target_ids") if isinstance(item.get("coverage_target_ids"), list) else []
        coverage = [str(target).strip() for target in coverage_targets if str(target).strip()]
        if coverage:
            typer.echo(f"  coverage_targets: {', '.join(coverage[:6])}", err=True)
    if len(summaries) > 5:
        typer.echo(f"active_known_evidence_refs_more: {len(summaries) - 5}", err=True)


def _print_agent_submit_submitted_dispatch(result: dict) -> None:
    submitted_dispatch = result.get("submitted_dispatch")
    if not isinstance(submitted_dispatch, dict) or not submitted_dispatch:
        return
    plain_parts = _agent_submit_dispatch_plain_parts(submitted_dispatch)
    if plain_parts:
        typer.echo(f"submitted_dispatch: {', '.join(plain_parts)}", err=True)


def _agent_submit_dispatch_plain_parts(dispatch: dict) -> list[str]:
    parts: list[str] = []
    for key in ("run_id", "step_id", "iter", "step_order", "target_agent", "actual_agent", "dispatch_mode", "inline"):
        value = dispatch.get(key)
        if value in ("", None):
            continue
        parts.append(f"{key}={value}")
    return parts
