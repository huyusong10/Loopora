from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.evidence_manifest_artifacts import artifact_manifest, evidence_ref_is_direct_proof
from loopora.evidence_manifest_targets import coverage_target_refs, manifest_coverage_results, target_index
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import read_json, utc_now, write_json


def write_evidence_manifest_projection(layout: RunArtifactLayout, *, coverage_projection: Mapping[str, Any] | None = None) -> dict:
    projection = build_evidence_manifest_projection(layout, coverage_projection=coverage_projection)
    write_json(layout.evidence_manifest_path, projection)
    return projection


def build_evidence_manifest_projection(
    layout: RunArtifactLayout,
    *,
    coverage_projection: Mapping[str, Any] | None = None,
) -> dict:
    run_contract = _safe_read_json_artifact(layout.run_contract_path)
    coverage = dict(coverage_projection or _safe_read_json_artifact(layout.evidence_coverage_path))
    targets_by_id = {
        str(target.get("id") or "").strip(): target
        for target in list(coverage.get("targets") or [])
        if isinstance(target, Mapping) and str(target.get("id") or "").strip()
    }
    claims = [
        _claim_manifest(item, layout=layout, targets_by_id=targets_by_id) for item in read_jsonl(layout.evidence_ledger_path) if isinstance(item, Mapping)
    ]
    targets = target_index(targets_by_id, claims)
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "manifest_path": layout.relative(layout.evidence_manifest_path),
        "ledger_path": layout.relative(layout.evidence_ledger_path),
        "coverage_path": layout.relative(layout.evidence_coverage_path),
        "run_contract_path": layout.relative(layout.run_contract_path),
        "completion_mode": str(run_contract.get("completion_mode") or "gatekeeper"),
        "claim_count": len(claims),
        "artifact_backed_claim_count": sum(1 for claim in claims if claim["artifact_backed"]),
        "workspace_backed_claim_count": sum(1 for claim in claims if claim["workspace_backed"]),
        "direct_proof_claim_count": sum(1 for claim in claims if claim["verification_status"] == "direct_proof"),
        "workspace_artifact_claim_count": sum(1 for claim in claims if claim["verification_status"] == "workspace_artifact"),
        "run_artifact_claim_count": sum(1 for claim in claims if claim["verification_status"] == "run_artifact"),
        "ledger_only_claim_count": sum(1 for claim in claims if claim["verification_status"] == "ledger_only"),
        "unverified_claim_count": sum(1 for claim in claims if claim["verification_status"] == "unverified"),
        "claims": claims,
        "targets": targets,
        "problems": _manifest_problems(claims),
    }


def _claim_manifest(item: Mapping[str, Any], *, layout: RunArtifactLayout, targets_by_id: Mapping[str, Mapping[str, Any]]) -> dict:
    artifact_refs = [artifact_manifest(ref) for ref in list(item.get("artifact_refs") or []) if isinstance(ref, Mapping)]
    coverage_targets = coverage_target_refs(item, targets_by_id)
    workspace_backed = any(ref.get("kind") == "workspace" and ref.get("exists") for ref in artifact_refs)
    artifact_backed = any(ref.get("exists") for ref in artifact_refs)
    proof_backed = any(evidence_ref_is_direct_proof(ref) and ref.get("exists") for ref in artifact_refs)
    verification_status = _verification_status(
        result=str(item.get("result") or ""),
        artifact_backed=artifact_backed,
        workspace_backed=workspace_backed,
        proof_backed=proof_backed,
    )
    return {
        "id": str(item.get("id") or "").strip(),
        "claim": str(item.get("claim") or "").strip(),
        "producer": {
            "iter": structured_non_negative_int(item.get("iter")),
            "step_id": str(item.get("step_id") or "").strip(),
            "step_order": structured_non_negative_int(item.get("step_order")),
            "role_id": str(item.get("role_id") or "").strip(),
            "role_name": str(item.get("role_name") or "").strip(),
            "runtime_role": str(item.get("runtime_role") or "").strip(),
            "archetype": str(item.get("archetype") or "").strip(),
        },
        "evidence_kind": str(item.get("evidence_kind") or "").strip(),
        "source": str(item.get("source") or "").strip(),
        "method": str(item.get("method") or "").strip(),
        "result": str(item.get("result") or "").strip(),
        "verifies": [str(value).strip() for value in list(item.get("verifies") or []) if str(value).strip()],
        "coverage_results": manifest_coverage_results(item.get("coverage_results")),
        "coverage_targets": coverage_targets,
        "related_evidence_ids": [str(value).strip() for value in list(item.get("related_evidence_ids") or []) if str(value).strip()][:20],
        "artifact_refs": artifact_refs,
        "artifact_count": len(artifact_refs),
        "workspace_artifact_count": sum(1 for ref in artifact_refs if ref.get("kind") == "workspace"),
        "artifact_backed": artifact_backed,
        "workspace_backed": workspace_backed,
        "measured_evidence": structured_bool_is_true(item.get("measured_evidence")),
        "concrete_evidence_claim_count": structured_non_negative_int(item.get("concrete_evidence_claim_count")),
        "verification_status": verification_status,
        "reproducible": verification_status in {"direct_proof", "workspace_artifact"},
        "residual_risk": str(item.get("residual_risk") or "").strip(),
        "manifest_ref": f"{layout.relative(layout.evidence_manifest_path)}#{str(item.get('id') or '').strip()}",
    }


def _verification_status(
    *,
    result: str,
    artifact_backed: bool,
    workspace_backed: bool,
    proof_backed: bool,
) -> str:
    normalized_result = result.strip().lower()
    if normalized_result in {"blocked", "failed", "rejected"}:
        return "unverified"
    if proof_backed:
        return "direct_proof"
    if workspace_backed:
        return "workspace_artifact"
    if artifact_backed:
        return "run_artifact"
    return "ledger_only"


def _manifest_problems(claims: list[dict]) -> list[dict]:
    problems = []
    for claim in claims:
        claim_id = str(claim.get("id") or "").strip()
        if claim.get("verification_status") == "ledger_only":
            problems.append(
                {
                    "code": "claim_without_artifact",
                    "claim_id": claim_id,
                    "severity": "weak",
                    "message": "Evidence claim has no artifact refs.",
                }
            )
        missing_artifacts = [
            str(ref.get("label") or ref.get("relative_path") or "").strip() for ref in claim.get("artifact_refs") or [] if not ref.get("exists")
        ]
        if missing_artifacts:
            problems.append(
                {
                    "code": "claim_artifact_missing",
                    "claim_id": claim_id,
                    "severity": "weak",
                    "message": "Evidence claim references missing artifacts.",
                    "artifacts": missing_artifacts[:6],
                }
            )
    return problems[:40]


def _safe_read_json_artifact(path: Path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
