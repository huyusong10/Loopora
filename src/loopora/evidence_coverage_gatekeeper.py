from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.evidence_support import evidence_item_is_non_supporting_gatekeeper_ref, evidence_item_is_supporting_gatekeeper_ref
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int


def latest_gatekeeper_projection(
    item: Mapping[str, Any],
    *,
    item_id: str,
    risk: str,
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
) -> dict:
    if str(item.get("archetype") or "").strip().lower() != "gatekeeper":
        return {}
    gatekeeper_refs = _gatekeeper_evidence_refs(item)
    return {
        "id": item_id,
        "result": str(item.get("result") or "").strip(),
        "evidence_refs": gatekeeper_refs,
        "supporting_evidence_refs": _supporting_gatekeeper_refs(gatekeeper_refs, evidence_items_by_id),
        "non_supporting_evidence_refs": _non_supporting_gatekeeper_refs(gatekeeper_refs, evidence_items_by_id, current_id=item_id),
        "self_measured_evidence": gatekeeper_has_self_measured_evidence(item, item_id=item_id, evidence_refs=gatekeeper_refs),
        "self_evidence_claim_count": structured_non_negative_int(item.get("concrete_evidence_claim_count")),
        "residual_risk": risk,
    }


def apply_gatekeeper_target(target_state: dict[str, dict], latest_gatekeeper: Mapping[str, Any]) -> None:
    row = target_state.get("gatekeeper.finish")
    if not row or not latest_gatekeeper:
        return
    result = str(latest_gatekeeper.get("result") or "").strip().lower()
    gatekeeper_id = str(latest_gatekeeper.get("id") or "").strip()
    evidence_refs = [str(item).strip() for item in list(latest_gatekeeper.get("evidence_refs") or []) if str(item).strip()]
    supporting_refs = [str(item).strip() for item in list(latest_gatekeeper.get("supporting_evidence_refs") or []) if str(item).strip()]
    non_supporting_refs = [str(item).strip() for item in list(latest_gatekeeper.get("non_supporting_evidence_refs") or []) if str(item).strip()]
    has_self_measured_evidence = structured_bool_is_true(latest_gatekeeper.get("self_measured_evidence"))
    if result == "passed" and supporting_refs:
        row["status"] = "covered"
        row["reason"] = "GateKeeper passed with supporting upstream evidence refs."
        row["evidence_refs"] = list(dict.fromkeys([*supporting_refs, gatekeeper_id]))
    elif result == "passed" and has_self_measured_evidence:
        row["status"] = "covered"
        row["reason"] = "GateKeeper passed with measured self evidence and concrete evidence claims."
        row["evidence_refs"] = [gatekeeper_id] if gatekeeper_id else []
    elif result == "passed" and evidence_refs and non_supporting_refs and not supporting_refs:
        row["status"] = "blocked"
        row["reason"] = "GateKeeper pass cited only non-supporting upstream evidence refs."
        row["evidence_refs"] = list(dict.fromkeys([*non_supporting_refs, gatekeeper_id]))
    elif result in {"blocked", "failed", "rejected"}:
        row["status"] = "blocked"
        row["reason"] = "GateKeeper blocked the run."
        row["evidence_refs"] = [gatekeeper_id] if gatekeeper_id else []


def gatekeeper_has_self_measured_evidence(item: Mapping[str, Any], *, item_id: str, evidence_refs: list[str]) -> bool:
    if not item_id or item_id not in set(evidence_refs):
        return False
    if str(item.get("result") or "").strip().lower() != "passed":
        return False
    return structured_bool_is_true(item.get("measured_evidence")) and structured_non_negative_int(item.get("concrete_evidence_claim_count")) > 0


def _gatekeeper_evidence_refs(item: Mapping[str, Any]) -> list[str]:
    refs = [
        str(ref).split(":", 1)[1].strip()
        for ref in list(item.get("verifies") or [])
        if str(ref).startswith("evidence:") and str(ref).split(":", 1)[1].strip()
    ]
    if refs:
        return list(dict.fromkeys(refs))
    return list(
        dict.fromkeys(str(ref).strip() for ref in list(item.get("related_evidence_ids") or []) if str(ref).strip())
    )


def _supporting_gatekeeper_refs(evidence_refs: list[str], evidence_items_by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for ref in evidence_refs:
        item = evidence_items_by_id.get(str(ref).strip())
        if not item:
            continue
        if evidence_item_is_supporting_gatekeeper_ref(item):
            refs.append(str(ref).strip())
    return list(dict.fromkeys(refs))


def _non_supporting_gatekeeper_refs(
    evidence_refs: list[str],
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
    *,
    current_id: str,
) -> list[str]:
    refs: list[str] = []
    for ref in evidence_refs:
        if str(ref).strip() == str(current_id or "").strip():
            continue
        item = evidence_items_by_id.get(str(ref).strip())
        if not item:
            continue
        if evidence_item_is_non_supporting_gatekeeper_ref(item):
            refs.append(str(ref).strip())
    return list(dict.fromkeys(refs))
