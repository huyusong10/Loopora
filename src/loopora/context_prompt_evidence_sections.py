from __future__ import annotations

import json

from loopora.context_value_helpers import string_list as _string_list
from loopora.evidence_support import evidence_item_is_supporting_gatekeeper_ref
from loopora.residual_risk_support import residual_risk_is_meaningful
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int


def render_evidence_section(evidence: dict) -> str:
    items = list(evidence.get("items") or [])
    ledger_path = str(evidence.get("ledger_path") or "").strip()
    manifest_path = str(evidence.get("manifest_path") or "").strip()
    coverage_path = str(evidence.get("coverage_path") or "").strip()
    manifest_summary = evidence.get("manifest_summary") if isinstance(evidence.get("manifest_summary"), dict) else {}
    manifest_claims = _manifest_claims_by_id(evidence.get("manifest_claims"))
    lines = ["Evidence ledger:"]
    if ledger_path:
        lines.append(f"- Path: {ledger_path}")
    if manifest_path:
        lines.append(f"- Manifest: {manifest_path}")
    if coverage_path:
        lines.append(f"- Coverage: {coverage_path}")
    summary_line = _manifest_summary_prompt_line(manifest_summary)
    if summary_line:
        lines.append(summary_line)
    known_ids = [str(item).strip() for item in list(evidence.get("known_ids") or []) if str(item).strip()]
    if known_ids:
        lines.append(f"- Known ids: {json.dumps(known_ids[-40:], ensure_ascii=False)}")
    if not items:
        lines.append("- No evidence items have been written yet.")
        return "\n".join(lines)
    for item in items[-12:]:
        lines.extend(_evidence_item_prompt_lines(item, manifest_claims))
    return "\n".join(lines)


def _evidence_item_prompt_lines(item: object, manifest_claims: dict[str, dict]) -> list[str]:
    if not isinstance(item, dict):
        return []
    lines = [f"- {item.get('id', '-')}: {item.get('role_name', '-')} ({item.get('archetype', '-')}) ::{item.get('result', '-')} :: {item.get('claim', '-')}"]
    lines.append(f"  gatekeeper_support={_gatekeeper_support_prompt_value(item)}")
    lines.extend(_manifest_claim_prompt_lines(manifest_claims.get(str(item.get("id") or "").strip())))
    related = item.get("related_evidence_ids") if isinstance(item.get("related_evidence_ids"), list) else []
    if related:
        lines.append(f"  related={json.dumps(related, ensure_ascii=False)}")
    residual_risk = str(item.get("residual_risk") or "").strip()
    if residual_risk_is_meaningful(residual_risk):
        lines.append(f"  residual_risk={residual_risk}")
    coverage_results = _evidence_item_prompt_coverage_results(item.get("coverage_results"))
    if coverage_results:
        lines.append(f"  coverage_results={json.dumps(coverage_results, ensure_ascii=False)}")
    artifacts = _artifact_ref_prompt_paths(item.get("artifact_refs"))
    if artifacts:
        lines.append(f"  artifacts={json.dumps(artifacts, ensure_ascii=False)}")
    return lines


def _gatekeeper_support_prompt_value(item: dict) -> str:
    return "supporting" if evidence_item_is_supporting_gatekeeper_ref(item) else "non_supporting"


def _evidence_item_prompt_coverage_results(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id:
            continue
        rows.append(
            {
                "target_id": target_id,
                "status": str(item.get("status") or "").strip(),
                "evidence_refs": _string_list(item.get("evidence_refs"))[:8],
            }
        )
    return rows[:8]


def _manifest_claims_by_id(value: object) -> dict[str, dict]:
    return {str(claim.get("id") or "").strip(): claim for claim in list(value or []) if isinstance(claim, dict) and str(claim.get("id") or "").strip()}


def _manifest_summary_prompt_line(summary: dict) -> str:
    if not summary:
        return ""
    return (
        "- Proof strength: "
        f"claims={_int_value(summary.get('claim_count'))}, "
        f"direct_proof={_int_value(summary.get('direct_proof_claim_count'))}, "
        f"workspace_artifact={_int_value(summary.get('workspace_artifact_claim_count'))}, "
        f"run_artifact={_int_value(summary.get('run_artifact_claim_count'))}, "
        f"ledger_only={_int_value(summary.get('ledger_only_claim_count'))}, "
        f"unverified={_int_value(summary.get('unverified_claim_count'))}, "
        f"problems={_int_value(summary.get('problem_count'))}"
    )


def _manifest_claim_prompt_lines(claim: dict | None) -> list[str]:
    if not isinstance(claim, dict):
        return []
    lines = [
        "  "
        f"proof_status={claim.get('verification_status') or 'unknown'} "
        f"measured={_prompt_bool(claim.get('measured_evidence'))} "
        f"concrete_claims={_int_value(claim.get('concrete_evidence_claim_count'))} "
        f"artifact_backed={_prompt_bool(claim.get('artifact_backed'))} "
        f"workspace_backed={_prompt_bool(claim.get('workspace_backed'))} "
        f"reproducible={_prompt_bool(claim.get('reproducible'))} "
        f"coverage_targets={json.dumps(list(claim.get('coverage_targets') or [])[:8], ensure_ascii=False)}"
    ]
    problem_codes = [str(code).strip() for code in list(claim.get("problem_codes") or []) if str(code).strip()]
    if problem_codes:
        lines.append(f"  proof_problems={json.dumps(problem_codes[:8], ensure_ascii=False)}")
    return lines


def _prompt_bool(value: object) -> str:
    return "true" if structured_bool_is_true(value) else "false"


def _artifact_ref_prompt_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths: list[str] = []
    refs = [ref for ref in value if isinstance(ref, dict)]
    refs = [
        *[ref for ref in refs if str(ref.get("kind") or "").strip() == "workspace"],
        *[ref for ref in refs if str(ref.get("kind") or "").strip() != "workspace"],
    ]
    for ref in refs:
        label = str(ref.get("label") or ref.get("kind") or "artifact").strip()
        workspace_path = str(ref.get("workspace_path") or "").strip()
        relative_path = str(ref.get("relative_path") or "").strip()
        absolute_path = str(ref.get("absolute_path") or "").strip()
        if not workspace_path and not relative_path:
            continue
        if workspace_path and relative_path and workspace_path != relative_path:
            path_text = f"{label}: {workspace_path} (run-local: {relative_path})"
        else:
            path_text = f"{label}: {workspace_path or relative_path}"
        if absolute_path:
            path_text = f"{path_text} (absolute: {absolute_path})"
        paths.append(path_text)
        if len(paths) >= 4:
            break
    return paths


def render_artifact_refs(refs: list[dict]) -> str:
    lines = ["Artifact refs:"]
    for ref in refs:
        workspace_path = str(ref.get("workspace_path") or ref.get("relative_path") or "").strip()
        relative_path = str(ref.get("relative_path") or "").strip()
        absolute_path = str(ref.get("absolute_path") or "").strip()
        if relative_path and workspace_path and workspace_path != relative_path:
            path_text = f"- {ref['label']}: {workspace_path} (run-local: {relative_path})"
        else:
            path_text = f"- {ref['label']}: {workspace_path or relative_path}"
        if absolute_path:
            path_text = f"{path_text} (absolute: {absolute_path})"
        lines.append(path_text)
    return "\n".join(lines)


def _int_value(value: object) -> int:
    return structured_non_negative_int(value)
