from __future__ import annotations

from pathlib import Path

from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.run_takeaway_judgment import build_judgment_contract


ALIGNMENT_SOURCE_ARTIFACT_REF_KEYS = ("kind", "label", "relative_path", "workspace_path", "absolute_path")


def alignment_run_artifact_paths(run: dict) -> dict:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    return {
        "run_contract": layout.relative(layout.run_contract_path),
        "task_verdict": layout.relative(layout.task_verdict_path),
        "evidence_ledger": layout.relative(layout.evidence_ledger_path),
        "evidence_coverage": layout.relative(layout.evidence_coverage_path),
        "evidence_manifest": layout.relative(layout.evidence_manifest_path),
    }


def alignment_run_judgment_contract(run: dict) -> dict:
    return build_judgment_contract(run)


def alignment_source_string_list(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)][:limit]


def alignment_source_artifact_refs(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    refs: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                key: item.get(key, "") if isinstance(item.get(key, ""), str) else ""
                for key in ALIGNMENT_SOURCE_ARTIFACT_REF_KEYS
            }
        )
        if len(refs) >= limit:
            break
    return refs


def alignment_run_evidence_summary(run: dict, *, limit: int = 8) -> list[dict]:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    if not layout.evidence_ledger_path.exists():
        return []
    items = [
        {
            "id": str(item.get("id") or ""),
            "kind": str(item.get("evidence_kind") or ""),
            "archetype": str(item.get("archetype") or ""),
            "step_id": str(item.get("step_id") or ""),
            "claim": str(item.get("claim") or "")[:500],
            "result": str(item.get("result") or ""),
            "residual_risk": str(item.get("residual_risk") or "")[:300],
            "verifies": alignment_source_string_list(item.get("verifies"), limit=8),
            "artifact_refs": alignment_source_artifact_refs(item.get("artifact_refs"), limit=6),
        }
        for item in read_jsonl(layout.evidence_ledger_path)
    ]
    return items[-limit:]


def alignment_run_coverage_summary(run: dict) -> dict:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    projection = load_or_build_evidence_coverage_projection(layout)
    summary = summarize_evidence_coverage_projection(
        projection,
        coverage_path_available=layout.evidence_coverage_path.exists(),
    )
    return {
        "ledger_path": summary.get("ledger_path", ""),
        "status": summary.get("status", ""),
        "reason": (summary.get("summary") or {}).get("reason", ""),
        "coverage_path": summary.get("coverage_path", ""),
        "evidence_count": summary.get("evidence_count", 0),
        "check_count": summary.get("check_count", 0),
        "covered_check_count": summary.get("covered_check_count", 0),
        "missing_check_count": summary.get("missing_check_count", 0),
        "covered_check_ids": list(summary.get("covered_check_ids") or [])[:20],
        "missing_check_ids": list(summary.get("missing_check_ids") or [])[:20],
        "target_count": summary.get("target_count", 0),
        "covered_target_count": summary.get("covered_target_count", 0),
        "weak_target_count": summary.get("weak_target_count", 0),
        "missing_target_count": summary.get("missing_target_count", 0),
        "blocked_target_count": summary.get("blocked_target_count", 0),
        "top_gaps": list(summary.get("top_gaps") or [])[:5],
        "evidence_kind_counts": summary.get("evidence_kind_counts") or {},
        "artifact_ref_count": summary.get("artifact_ref_count", 0),
        "residual_risk_count": summary.get("residual_risk_count", 0),
        "risk_signals": list(summary.get("risk_signals") or [])[:5],
        "latest_gatekeeper": summary.get("latest_gatekeeper") or {},
    }
