from __future__ import annotations

from loopora.context_flow import normalize_manifest_claim_coverage_targets
from loopora.run_artifacts import RunArtifactLayout
from loopora.strategy_source import normalize_strategy_step_evidence_limit
from loopora.utils import structured_bool_is_true
from loopora.utils import structured_non_negative_int
from loopora.utils import read_json


def step_inputs(step: dict) -> dict:
    inputs = step.get("inputs")
    return dict(inputs) if isinstance(inputs, dict) else {}


def matches_handoff_selector(handoff: dict, selector: str) -> bool:
    source = handoff.get("source") if isinstance(handoff, dict) else {}
    if not isinstance(source, dict):
        return False
    normalized = str(selector or "").strip()
    return normalized in {
        str(source.get("step_id") or "").strip(),
        str(source.get("role_id") or "").strip(),
        str(source.get("runtime_role") or "").strip(),
        str(source.get("archetype") or "").strip(),
        str(source.get("role_name") or "").strip(),
    }


def filter_handoffs_for_step(step: dict, handoffs: list[dict]) -> list[dict]:
    selectors = [str(item).strip() for item in list(step_inputs(step).get("handoffs_from") or []) if str(item).strip()]
    if not selectors:
        return list(handoffs)
    return [handoff for handoff in handoffs if any(matches_handoff_selector(handoff, selector) for selector in selectors)]


def iteration_memory_for_step(
    step: dict,
    *,
    previous_iteration_same_step: dict | None,
    previous_iteration_same_role: dict | None,
    previous_iteration_summary: dict | None,
) -> tuple[dict | None, dict | None, dict | None]:
    policy = str(step_inputs(step).get("iteration_memory") or "default").strip().lower()
    if policy == "none":
        return None, None, None
    if policy == "same_step":
        return previous_iteration_same_step, None, None
    if policy == "same_role":
        return None, previous_iteration_same_role, None
    if policy == "summary_only":
        return None, None, previous_iteration_summary
    return previous_iteration_same_step, previous_iteration_same_role, previous_iteration_summary


def filter_evidence_for_step(step: dict, evidence_items: list[dict]) -> list[dict]:
    inputs = step_inputs(step)
    query = inputs.get("evidence_query") if isinstance(inputs.get("evidence_query"), dict) else {}
    archetypes = {str(item).strip() for item in list(query.get("archetypes") or []) if str(item).strip()}
    verifies = [str(item).strip().lower() for item in list(query.get("verifies") or []) if str(item).strip()]
    filtered: list[dict] = []
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        if archetypes and str(item.get("archetype") or "").strip() not in archetypes:
            continue
        if verifies:
            verify_text = " ".join(str(value) for value in list(item.get("verifies") or [])).lower()
            if not any(needle in verify_text for needle in verifies):
                continue
        filtered.append(item)
    limit = normalize_strategy_step_evidence_limit(query.get("limit")) or 40
    return filtered[-limit:]


def step_declares_evidence_query(step: dict) -> bool:
    query = step_inputs(step).get("evidence_query")
    return isinstance(query, dict) and bool(query)


def evidence_known_ids(evidence_items: list[dict]) -> list[str]:
    return list(
        dict.fromkeys(
            str(item.get("id"))
            for item in evidence_items
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        )
    )


def dedupe_evidence_items(evidence_items: list[dict]) -> list[dict]:
    unique_items: list[dict] = []
    seen_ids: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("id") or "").strip()
        if evidence_id:
            if evidence_id in seen_ids:
                continue
            seen_ids.add(evidence_id)
        unique_items.append(item)
    return unique_items


def coverage_gap_evidence_ids(coverage_summary: dict) -> list[str]:
    refs: list[str] = []
    summary = coverage_summary.get("summary") if isinstance(coverage_summary.get("summary"), dict) else {}
    primary_gap = summary.get("primary_gap") if isinstance(summary.get("primary_gap"), dict) else {}
    for item in [primary_gap, *list(coverage_summary.get("top_gaps") or [])]:
        if not isinstance(item, dict):
            continue
        refs.extend(str(ref).strip() for ref in list(item.get("evidence_refs") or []) if str(ref).strip())
    return list(dict.fromkeys(refs))


def merge_coverage_gap_evidence(
    evidence_items: list[dict],
    *,
    all_evidence_items: list[dict],
    coverage_summary: dict,
) -> tuple[list[dict], list[str]]:
    evidence_by_id = {
        str(item.get("id") or "").strip(): item
        for item in all_evidence_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    merged_items = [item for item in evidence_items if isinstance(item, dict)]
    merged_ids = {str(item.get("id") or "").strip() for item in merged_items if str(item.get("id") or "").strip()}
    for ref in coverage_gap_evidence_ids(coverage_summary):
        if ref in merged_ids or ref not in evidence_by_id:
            continue
        merged_items.append(evidence_by_id[ref])
        merged_ids.add(ref)
    return merged_items, evidence_known_ids(merged_items)


def manifest_prompt_context(layout: RunArtifactLayout, known_ids: list[str]) -> tuple[dict, list[dict]]:
    summary = empty_manifest_prompt_summary()
    try:
        manifest = read_json(layout.evidence_manifest_path)
    except (OSError, UnicodeError, ValueError):
        return summary, []
    if not isinstance(manifest, dict):
        return summary, []
    allowed_ids = {str(item).strip() for item in known_ids if str(item).strip()}
    problem_codes_by_claim: dict[str, list[str]] = {}
    for problem in list(manifest.get("problems") or []):
        if not isinstance(problem, dict):
            continue
        claim_id = str(problem.get("claim_id") or "").strip()
        code = str(problem.get("code") or "").strip()
        if claim_id and code:
            problem_codes_by_claim.setdefault(claim_id, []).append(code)
    claims = []
    for claim in list(manifest.get("claims") or []):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("id") or "").strip()
        if not claim_id or claim_id not in allowed_ids:
            continue
        claims.append(
            {
                "id": claim_id,
                "verification_status": str(claim.get("verification_status") or "ledger_only").strip(),
                "measured_evidence": structured_bool_is_true(claim.get("measured_evidence")),
                "concrete_evidence_claim_count": structured_non_negative_int(claim.get("concrete_evidence_claim_count")),
                "artifact_count": structured_non_negative_int(claim.get("artifact_count")),
                "artifact_backed": structured_bool_is_true(claim.get("artifact_backed")),
                "workspace_backed": structured_bool_is_true(claim.get("workspace_backed")),
                "reproducible": structured_bool_is_true(claim.get("reproducible")),
                "coverage_targets": normalize_manifest_claim_coverage_targets(claim.get("coverage_targets")),
                "problem_codes": problem_codes_by_claim.get(claim_id, [])[:8],
            }
        )
    summary = {
        "claim_count": len(claims),
        "direct_proof_claim_count": sum(1 for claim in claims if claim["verification_status"] == "direct_proof"),
        "workspace_artifact_claim_count": sum(1 for claim in claims if claim["verification_status"] == "workspace_artifact"),
        "run_artifact_claim_count": sum(1 for claim in claims if claim["verification_status"] == "run_artifact"),
        "ledger_only_claim_count": sum(1 for claim in claims if claim["verification_status"] == "ledger_only"),
        "unverified_claim_count": sum(1 for claim in claims if claim["verification_status"] == "unverified"),
        "problem_count": sum(len(claim["problem_codes"]) for claim in claims),
    }
    return summary, claims[-40:]


def empty_manifest_prompt_summary() -> dict:
    return {
        "claim_count": 0,
        "direct_proof_claim_count": 0,
        "workspace_artifact_claim_count": 0,
        "run_artifact_claim_count": 0,
        "ledger_only_claim_count": 0,
        "unverified_claim_count": 0,
        "problem_count": 0,
    }
