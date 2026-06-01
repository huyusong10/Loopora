from __future__ import annotations

import typer

from loopora.agent_native_evidence_refs import (
    agent_known_evidence_ref_summaries as _agent_known_evidence_ref_summaries,
    known_evidence_ref_items as _known_evidence_ref_items,
)
from loopora.agent_native_next_step_sections import (
    agent_current_step_evidence_scope_summary as _agent_current_step_evidence_scope_summary,
)


def print_agent_current_step_evidence_scope(next_step: dict) -> None:
    scope = _agent_current_step_evidence_scope_summary(next_step)
    if scope:
        typer.echo(f"known_evidence_scope: {scope}")


def print_agent_current_step_known_evidence(known_evidence_ids: object) -> None:
    if not isinstance(known_evidence_ids, list):
        return
    ids = [str(item).strip() for item in known_evidence_ids if str(item).strip()]
    if not ids:
        return
    displayed_ids = ids[-8:]
    if len(ids) > len(displayed_ids):
        typer.echo(f"known_evidence_ids_omitted: {len(ids) - len(displayed_ids)} older")
    typer.echo("known_evidence_ids:")
    for evidence_id in displayed_ids:
        typer.echo(f"- {evidence_id}")


def print_agent_current_step_known_evidence_refs(known_evidence_refs: object) -> None:
    summaries = _agent_known_evidence_ref_summaries(known_evidence_refs, limit=5)
    if not summaries:
        return
    refs = _known_evidence_ref_items(known_evidence_refs)
    omitted = max(0, len(refs) - len(summaries))
    if omitted:
        typer.echo(f"known_evidence_refs_omitted: {omitted} older")
    typer.echo("known_evidence_refs:")
    for item in summaries:
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
        typer.echo(f"- {' '.join(part for part in parts if part)}")
        claim = str(item.get("claim") or "").strip()
        if claim:
            typer.echo(f"  claim: {claim}")
        coverage_targets = item.get("coverage_target_ids") if isinstance(item.get("coverage_target_ids"), list) else []
        if coverage_targets:
            typer.echo(f"  coverage_targets: {', '.join(str(target) for target in coverage_targets)}")
        rendered_artifacts = _format_known_evidence_artifact_refs(item.get("artifact_refs"))
        if rendered_artifacts:
            typer.echo(f"  artifacts: {rendered_artifacts}")


def _format_known_evidence_artifact_refs(artifact_refs: object) -> str:
    if not isinstance(artifact_refs, list):
        return ""
    rendered_refs: list[str] = []
    for ref in artifact_refs[:4]:
        if not isinstance(ref, dict):
            continue
        label = str(ref.get("label") or "").strip()
        path = str(ref.get("path") or "").strip()
        if path:
            rendered_refs.append(f"{label}: {path}" if label else path)
    return "; ".join(rendered_refs)
