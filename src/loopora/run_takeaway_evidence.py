from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout
from loopora.run_takeaway_common import _int_value, _string_list, _string_value, safe_read_json_file

EVIDENCE_COVERAGE_COUNT_FIELDS = (
    "evidence_count",
    "check_count",
    "covered_check_count",
    "missing_check_count",
    "target_count",
    "covered_target_count",
    "weak_target_count",
    "missing_target_count",
    "blocked_target_count",
    "artifact_ref_count",
    "residual_risk_count",
)
EVIDENCE_COVERAGE_STATUSES = {"pending", "covered", "weak", "partial", "blocked", "legacy"}
EVIDENCE_MANIFEST_COUNT_FIELDS = (
    "claim_count",
    "artifact_backed_claim_count",
    "workspace_backed_claim_count",
    "direct_proof_claim_count",
    "workspace_artifact_claim_count",
    "run_artifact_claim_count",
    "ledger_only_claim_count",
    "unverified_claim_count",
)


def empty_evidence_coverage() -> dict[str, Any]:
    return {
        "ledger_path": "",
        "coverage_path": "",
        "status": "pending",
        "summary": {},
        "evidence_count": 0,
        "check_count": 0,
        "covered_check_count": 0,
        "missing_check_count": 0,
        "covered_check_ids": [],
        "missing_check_ids": [],
        "target_count": 0,
        "covered_target_count": 0,
        "weak_target_count": 0,
        "missing_target_count": 0,
        "blocked_target_count": 0,
        "top_gaps": [],
        "evidence_kind_counts": {},
        "artifact_ref_count": 0,
        "residual_risk_count": 0,
        "risk_signals": [],
        "latest_gatekeeper": {},
    }


def empty_evidence_manifest() -> dict[str, Any]:
    return {
        "manifest_path": "",
        "claim_count": 0,
        "artifact_backed_claim_count": 0,
        "workspace_backed_claim_count": 0,
        "direct_proof_claim_count": 0,
        "workspace_artifact_claim_count": 0,
        "run_artifact_claim_count": 0,
        "ledger_only_claim_count": 0,
        "unverified_claim_count": 0,
        "problem_count": 0,
        "problems": [],
    }


def build_task_verdict_artifact_path(run: dict) -> str:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if not runs_dir_value:
        return ""
    layout = RunArtifactLayout(Path(runs_dir_value))
    return layout.relative(layout.task_verdict_path) if layout.task_verdict_path.exists() else ""


def build_evidence_coverage(run: dict) -> dict[str, Any]:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if not runs_dir_value:
        return empty_evidence_coverage()

    layout = RunArtifactLayout(Path(runs_dir_value))
    projection = load_or_build_evidence_coverage_projection(layout)
    return summarize_evidence_coverage_projection(
        projection,
        coverage_path_available=layout.evidence_coverage_path.exists(),
    )


def normalize_evidence_coverage_payload(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    normalized = empty_evidence_coverage()
    normalized["ledger_path"] = _string_value(raw.get("ledger_path"))
    normalized["coverage_path"] = _string_value(raw.get("coverage_path"))
    normalized["status"] = _normalize_evidence_coverage_status(raw.get("status"))
    normalized["summary"] = dict(raw.get("summary") or {}) if isinstance(raw.get("summary"), Mapping) else {}
    for field in EVIDENCE_COVERAGE_COUNT_FIELDS:
        normalized[field] = _int_value(raw.get(field), default=0) or 0
    normalized["covered_check_ids"] = _string_list(raw.get("covered_check_ids"))
    normalized["missing_check_ids"] = _string_list(raw.get("missing_check_ids"))
    normalized["top_gaps"] = [dict(item) for item in list(raw.get("top_gaps") or []) if isinstance(item, Mapping)][:5]
    normalized["evidence_kind_counts"] = dict(raw.get("evidence_kind_counts") or {}) if isinstance(raw.get("evidence_kind_counts"), Mapping) else {}
    normalized["risk_signals"] = _string_list(raw.get("risk_signals"))[:5]
    normalized["latest_gatekeeper"] = dict(raw.get("latest_gatekeeper") or {}) if isinstance(raw.get("latest_gatekeeper"), Mapping) else {}
    return normalized


def _normalize_evidence_coverage_status(value: object) -> str:
    status = _string_value(value).lower()
    return status if status in EVIDENCE_COVERAGE_STATUSES else "pending"


def normalize_evidence_manifest_payload(value: object, *, default_manifest_path: str = "") -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    normalized = empty_evidence_manifest()
    normalized["manifest_path"] = _string_value(raw.get("manifest_path")) or default_manifest_path
    for field in EVIDENCE_MANIFEST_COUNT_FIELDS:
        normalized[field] = _int_value(raw.get(field), default=0) or 0
    problems = [dict(item) for item in list(raw.get("problems") or []) if isinstance(item, Mapping)]
    normalized["problem_count"] = len(problems) if isinstance(raw.get("problems"), list) else (_int_value(raw.get("problem_count"), default=0) or 0)
    normalized["problems"] = [
        {
            "code": _string_value(item.get("code")),
            "claim_id": _string_value(item.get("claim_id")),
            "severity": _string_value(item.get("severity")),
            "message": _string_value(item.get("message")),
        }
        for item in problems[:4]
    ]
    return normalized


def build_evidence_manifest(run: dict) -> dict[str, Any]:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if not runs_dir_value:
        return empty_evidence_manifest()

    layout = RunArtifactLayout(Path(runs_dir_value))
    manifest = safe_read_json_file(layout.evidence_manifest_path)
    if not manifest:
        return empty_evidence_manifest()
    return normalize_evidence_manifest_payload(
        manifest,
        default_manifest_path=layout.relative(layout.evidence_manifest_path),
    )
