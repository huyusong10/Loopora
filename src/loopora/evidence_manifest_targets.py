from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.evidence_coverage_targets import parse_target_verify_ref
from loopora.evidence_manifest_artifacts import artifact_manifest, dedupe_artifact_refs


def coverage_target_refs(item: Mapping[str, Any], targets_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict]:
    refs = []
    seen: set[str] = set()
    for coverage_result in manifest_coverage_results(item.get("coverage_results")):
        target_id = coverage_result["target_id"]
        if target_id in seen:
            continue
        seen.add(target_id)
        target = targets_by_id.get(target_id, {})
        refs.append(
            {
                "id": target_id,
                "kind": str(target.get("kind") or "").strip(),
                "label": str(target.get("label") or target_id).strip(),
                "reported_status": coverage_result["status"],
                "coverage_status": str(target.get("status") or "missing").strip(),
                "required": coverage_target_is_required(target, target_id=target_id),
                "evidence_refs": coverage_result["evidence_refs"],
            }
        )
    for verify_ref in list(item.get("verifies") or []):
        parsed = parse_target_verify_ref(verify_ref)
        if not parsed:
            continue
        target_id, reported_status = parsed
        if target_id in seen:
            continue
        seen.add(target_id)
        target = targets_by_id.get(target_id, {})
        refs.append(
            {
                "id": target_id,
                "kind": str(target.get("kind") or "").strip(),
                "label": str(target.get("label") or target_id).strip(),
                "reported_status": str(reported_status or "unknown").strip(),
                "coverage_status": str(target.get("status") or "missing").strip(),
                "required": coverage_target_is_required(target, target_id=target_id),
                "evidence_refs": [],
            }
        )
    return refs


def manifest_coverage_results(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    results: list[dict] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id or ":" in target_id:
            continue
        results.append(
            {
                "target_id": target_id,
                "status": str(item.get("status") or "unknown").strip() or "unknown",
                "evidence_refs": [str(value).strip() for value in list(item.get("evidence_refs") or []) if str(value).strip()][:20],
                "note": str(item.get("note") or "").strip()[:400],
            }
        )
    return results[:20]


def target_index(targets_by_id: Mapping[str, Mapping[str, Any]], claims: list[dict]) -> list[dict]:
    claims_by_target: dict[str, list[str]] = {}
    artifacts_by_target: dict[str, list[dict]] = {}
    claims_by_id = {str(claim.get("id") or "").strip(): claim for claim in claims if str(claim.get("id") or "").strip()}
    for target_id, target in targets_by_id.items():
        target_artifacts = [artifact_manifest(ref) for ref in list(target.get("artifact_refs") or []) if isinstance(ref, Mapping)]
        if target_artifacts:
            artifacts_by_target.setdefault(target_id, []).extend(dict(ref) for ref in target_artifacts[:8])
    for claim in claims:
        claim_id = str(claim.get("id") or "").strip()
        for target_ref in claim.get("coverage_targets") or []:
            target_id = str(target_ref.get("id") or "").strip()
            if not target_id:
                continue
            claims_by_target.setdefault(target_id, []).append(claim_id)
            artifacts_by_target.setdefault(target_id, []).extend(list(claim.get("artifact_refs") or [])[:4])
    for target_id, target in targets_by_id.items():
        for evidence_ref in list(target.get("evidence_refs") or []):
            claim = claims_by_id.get(str(evidence_ref or "").strip())
            if not claim:
                continue
            claims_by_target.setdefault(target_id, []).append(str(claim.get("id") or "").strip())
            artifacts_by_target.setdefault(target_id, []).extend(list(claim.get("artifact_refs") or [])[:4])
    return [
        {
            "id": target_id,
            "kind": str(target.get("kind") or "").strip(),
            "label": str(target.get("label") or target_id).strip(),
            "status": str(target.get("status") or "missing").strip(),
            "required": coverage_target_is_required(target, target_id=target_id),
            "claim_refs": list(dict.fromkeys(claims_by_target.get(target_id, []))),
            "artifact_refs": dedupe_artifact_refs(artifacts_by_target.get(target_id, []))[:8],
        }
        for target_id, target in targets_by_id.items()
    ]
