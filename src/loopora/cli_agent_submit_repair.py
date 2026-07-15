from __future__ import annotations

from pathlib import Path

from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_submit_repair_results import (
    _active_agent_native_step_view as _active_agent_native_step_view,
    _agent_submit_core_blocker_kind as _agent_submit_core_blocker_kind,
    _agent_submit_error_is_repairable as _agent_submit_error_is_repairable,
    _agent_submit_next_repair_step as _agent_submit_next_repair_step,
    _agent_submit_repair_focus as _agent_submit_repair_focus,
    _agent_submit_repair_result as _agent_submit_repair_result,
)
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import (
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)

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

_print_agent_submit_repair_plain = print_agent_submit_repair_plain


def _print_agent_submit_repair_guidance(
    exc: Exception,
    *,
    service,
    adapter: str,
    context_id: str,
    run_id: str,
    entry_source: str,
    result_file: Path,
    workdir: Path,
    json_output: bool,
    auto_repair_actions: list[str] | None = None,
) -> bool:
    result = _agent_submit_repair_result(
        exc,
        service=service,
        adapter=adapter,
        context_id=context_id,
        run_id=run_id,
        entry_source=entry_source,
        result_file=result_file,
        workdir=workdir,
        auto_repair_actions=auto_repair_actions or [],
    )
    if not result:
        return False
    if json_output:
        echo_json(_agent_submit_repair_json_payload(result))
        return True
    _print_agent_submit_repair_plain(result)
    return True


def _agent_submit_repair_json_payload(result: dict) -> dict:
    summary = _agent_submit_repair_summary(result)
    return _agent_v3_envelope(
        kind="agent_submit_repair",
        status="blocked",
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_submit_repair_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_submit_repair_summary", summary=summary, payload=result),
        },
    )


def _agent_submit_repair_summary(result: dict) -> dict:
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "submit_repair": str(result.get("submit_repair") or "").strip(),
    }
    attach_native_run_surface(summary, result)
    for key in (
        "run_id",
        "context_id",
        "result_file_to_repair",
        "active_step_id",
        "active_role",
        "active_target_agent",
        "active_result_template",
        "active_result_file_to_write",
        "next_repair_step",
        "schema_lookup",
        "core_blocker_kind",
    ):
        _set_summary_text(summary, key, result.get(key))
    if result.get("auto_repair_attempted") is True:
        summary["auto_repair_attempted"] = True
    if result.get("core_blocker_preserved") is True:
        summary["core_blocker_preserved"] = True
    _set_summary_list(summary, "auto_repair_actions", result.get("auto_repair_actions"))
    for key in ("active_iter", "active_step_order"):
        value = result.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            summary[key] = value
    if result.get("submitted_template_file") is True:
        summary["submitted_template_file"] = True
    submitted_dispatch = result.get("submitted_dispatch")
    if isinstance(submitted_dispatch, dict) and submitted_dispatch:
        summary["submitted_dispatch"] = submitted_dispatch
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_list(summary, "active_known_evidence_ids", result.get("active_known_evidence_ids"))
    if isinstance(result.get("active_known_evidence_refs"), list) and result.get("active_known_evidence_refs"):
        summary["active_known_evidence_refs"] = result["active_known_evidence_refs"]
    _set_summary_list(summary, "active_coverage_target_ids", result.get("active_coverage_target_ids"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}
