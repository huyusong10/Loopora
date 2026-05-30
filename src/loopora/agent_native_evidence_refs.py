from __future__ import annotations

from loopora.cli_summary_helpers import clip_inline, set_summary_text
from loopora.run_artifacts import RunArtifactLayout, read_jsonl


def known_evidence_ref_items(known_evidence_refs: object) -> list[dict]:
    if not isinstance(known_evidence_refs, list):
        return []
    return [item for item in known_evidence_refs if isinstance(item, dict)]


def agent_known_evidence_ref_summaries(known_evidence_refs: object, *, limit: int) -> list[dict[str, object]]:
    refs = known_evidence_ref_items(known_evidence_refs)
    if not refs:
        return []
    displayed = refs[-limit:]
    summaries: list[dict[str, object]] = []
    for item in displayed:
        summary: dict[str, object] = {}
        set_summary_text(summary, "id", item.get("id"))
        set_summary_text(summary, "step_id", item.get("step_id"))
        set_summary_text(summary, "role_name", item.get("role_name"))
        set_summary_text(summary, "result", item.get("result"))
        set_summary_text(summary, "gatekeeper_support", item.get("gatekeeper_support"))
        set_summary_text(summary, "gatekeeper_support_reason", clip_inline(str(item.get("gatekeeper_support_reason") or ""), 160))
        set_summary_text(summary, "claim", clip_inline(str(item.get("claim") or ""), 220))
        coverage_value = item.get("coverage_target_ids")
        coverage_targets = [str(target).strip() for target in coverage_value if str(target).strip()] if isinstance(coverage_value, list) else []
        if coverage_targets:
            summary["coverage_target_ids"] = coverage_targets[:6]
        artifact_value = item.get("artifact_refs")
        artifact_refs = [
            {
                key: value
                for key, value in {
                    "label": clip_inline(str(artifact.get("label") or ""), 80),
                    "path": clip_inline(str(artifact.get("path") or ""), 160),
                }.items()
                if value
            }
            for artifact in artifact_value
            if isinstance(artifact, dict) and str(artifact.get("path") or "").strip()
        ] if isinstance(artifact_value, list) else []
        if artifact_refs:
            summary["artifact_refs"] = artifact_refs[:4]
        if summary:
            summaries.append(summary)
    return summaries


def agent_native_step_view_known_evidence_ids(
    *,
    known_evidence_ids: list[str] | None,
    layout: RunArtifactLayout,
) -> list[str]:
    if known_evidence_ids is not None:
        return list(dict.fromkeys(str(item) for item in known_evidence_ids if str(item).strip()))
    return list(
        dict.fromkeys(
            str(item.get("id"))
            for item in read_jsonl(layout.evidence_ledger_path)
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        )
    )
