from __future__ import annotations

from dataclasses import dataclass

from loopora.evidence_gate import concrete_evidence_claim_count, has_measured_gate_evidence
from loopora.evidence_support import (
    NON_SUPPORTING_EVIDENCE_RESULTS,
    evidence_item_is_non_supporting_gatekeeper_ref,
    evidence_item_is_supporting_gatekeeper_ref,
)


@dataclass(frozen=True)
class GatekeeperEvidenceContext:
    known_by_id: dict[str, dict]
    known_ids: set[str]
    current_id: str


@dataclass
class GatekeeperEvidenceGateState:
    result: dict
    evidence_refs: list[str]
    evidence_claims: list[str]
    metric_scores: dict
    context: GatekeeperEvidenceContext
    blocking_issues: list[str]


def build_gatekeeper_evidence_context(
    evidence_items: object,
    *,
    known_ids: list[str],
    current_evidence_id: str,
) -> GatekeeperEvidenceContext:
    known_by_id = {
        str(item.get("id") or "").strip(): item
        for item in list(evidence_items or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    known_id_set = set(known_by_id)
    known_id_set.update(known_ids)
    return GatekeeperEvidenceContext(
        known_by_id=known_by_id,
        known_ids=known_id_set,
        current_id=str(current_evidence_id or "").strip(),
    )


def expand_self_evidence_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    if not context.current_id:
        return evidence_refs
    return [context.current_id if item == "self" else item for item in evidence_refs]


def invalid_coverage_result_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [item for item in evidence_refs if item not in context.known_ids]


def apply_gatekeeper_evidence_gate(state: GatekeeperEvidenceGateState) -> list[str]:
    if not state.result["passed"]:
        return state.evidence_refs
    has_measured_evidence = has_measured_gate_evidence(state.metric_scores, state.result.get("metrics"))
    concrete_claims = concrete_evidence_claim_count(state.evidence_claims)
    evidence_refs = state.evidence_refs
    if not evidence_refs and state.context.current_id and concrete_claims > 0 and has_measured_evidence:
        evidence_refs = [state.context.current_id]

    invalid_refs = _invalid_evidence_refs(evidence_refs, state.context)
    supporting_refs = _supporting_upstream_refs(evidence_refs, state.context)
    blocking_non_supporting_refs = _blocking_non_supporting_upstream_refs(evidence_refs, state.context)
    if invalid_refs:
        state.blocking_issues.append(_invalid_ref_blocker(invalid_refs))
        state.result["passed"] = False
        evidence_refs = [
            item for item in evidence_refs if item == state.context.current_id or item in state.context.known_ids
        ]
    elif evidence_refs and not supporting_refs and blocking_non_supporting_refs:
        state.blocking_issues.append("gatekeeper_pass_refs_not_supporting_evidence")
        state.result["passed"] = False
    elif not supporting_refs and concrete_claims > 0 and has_measured_evidence and state.context.current_id:
        evidence_refs = list(dict.fromkeys([*evidence_refs, state.context.current_id]))
    elif not evidence_refs:
        state.blocking_issues.append("gatekeeper_pass_requires_evidence_refs")
        state.result["passed"] = False
    elif not supporting_refs and _non_supporting_upstream_refs(evidence_refs, state.context):
        state.blocking_issues.append("gatekeeper_pass_refs_not_supporting_evidence")
        state.result["passed"] = False
    elif not supporting_refs and not has_measured_evidence:
        state.blocking_issues.append("gatekeeper_pass_requires_upstream_or_measured_evidence")
        state.result["passed"] = False
    return evidence_refs


def _invalid_evidence_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [item for item in evidence_refs if item != context.current_id and item not in context.known_ids]


def _supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    return [
        item
        for item in evidence_refs
        if item != context.current_id
        and item in context.known_ids
        and evidence_item_is_supporting_gatekeeper_ref(context.known_by_id.get(item, {}))
    ]


def _non_supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    refs: list[str] = []
    for item in evidence_refs:
        if item == context.current_id or item not in context.known_ids:
            continue
        evidence_item = context.known_by_id.get(item, {})
        if evidence_item_is_non_supporting_gatekeeper_ref(evidence_item):
            refs.append(item)
    return refs


def _blocking_non_supporting_upstream_refs(evidence_refs: list[str], context: GatekeeperEvidenceContext) -> list[str]:
    refs: list[str] = []
    for item in evidence_refs:
        if item == context.current_id or item not in context.known_ids:
            continue
        evidence_item = context.known_by_id.get(item, {})
        if str(evidence_item.get("result") or "").strip().lower() in NON_SUPPORTING_EVIDENCE_RESULTS:
            refs.append(item)
    return refs


def _invalid_ref_blocker(invalid_refs: list[str]) -> str:
    return "gatekeeper_evidence_refs_unknown: " + ", ".join(invalid_refs[:4]) + (
        "..." if len(invalid_refs) > 4 else ""
    )
