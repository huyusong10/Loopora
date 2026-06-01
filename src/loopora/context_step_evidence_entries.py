from __future__ import annotations

"""Evidence entry projection from step handoffs."""

from typing import Protocol

from loopora.context_value_helpers import clean_text, evidence_coverage_results, string_list, unique_string_list
from loopora.evidence_gate import concrete_evidence_claim_count, has_measured_gate_evidence
from loopora.structured_numbers import coerced_non_negative_int
from loopora.utils import utc_now


class StepEvidenceResultContext(Protocol):
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    output: dict


class StepEvidenceEntryRequestLike(Protocol):
    result: StepEvidenceResultContext
    handoff: dict


def evidence_entry_id(iter_id: int, step_order: int, step_id: str) -> str:
    cleaned_step = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(step_id))
    return f"ev_{coerced_non_negative_int(iter_id):03d}_{coerced_non_negative_int(step_order):02d}_{cleaned_step}"


def build_step_evidence_entry(request: StepEvidenceEntryRequestLike) -> dict:
    result = request.result
    iter_id = coerced_non_negative_int(result.iter_id)
    step_order = coerced_non_negative_int(result.step_order)
    archetype = str(result.role["archetype"])
    current_evidence_id = evidence_entry_id(iter_id, step_order, result.step["id"])
    verifies = _evidence_verifies(archetype, result.output, current_evidence_id=current_evidence_id)
    related_evidence_ids = _related_evidence_ids(result.output, current_evidence_id=current_evidence_id)
    evidence_claims = string_list(result.output.get("evidence_claims"))
    claim = clean_text(result.output.get("decision_summary") if archetype == "gatekeeper" else request.handoff.get("summary"))
    if evidence_claims:
        claim = " ".join([claim, "Evidence:", "; ".join(evidence_claims[:4])]).strip()
    residual_risk = _evidence_residual_risk(archetype, result.output, request.handoff)
    control = result.step.get("control") if isinstance(result.step.get("control"), dict) else {}
    is_control = bool(result.step.get("control_id") or control)
    if is_control:
        claim, verifies, related_evidence_ids = _apply_control_context(
            control,
            claim=claim,
            verifies=verifies,
            related_evidence_ids=related_evidence_ids,
        )
    if not verifies:
        verifies = [_step_result_verify_ref(result.step["id"], request.handoff.get("status"))]
    return {
        "id": current_evidence_id,
        "timestamp": utc_now(),
        "iter": iter_id,
        "step_id": str(result.step["id"]),
        "step_order": step_order,
        "role_id": str(result.role["id"]),
        "role_name": str(result.role["name"]),
        "runtime_role": str(result.runtime_role),
        "archetype": archetype,
        "evidence_kind": "control" if is_control else _evidence_kind(archetype),
        "source": "workflow_control" if is_control else _evidence_source(archetype),
        "method": f"workflow_control:{control.get('signal', '')}" if is_control else _evidence_method(archetype),
        "claim": claim or "This step produced a workflow handoff.",
        "result": clean_text(request.handoff.get("status")) or "completed",
        "verifies": verifies,
        "related_evidence_ids": related_evidence_ids,
        "coverage_results": evidence_coverage_results(result.output.get("coverage_results")),
        "measured_evidence": has_measured_gate_evidence(result.output.get("metric_scores"), result.output.get("metrics")),
        "concrete_evidence_claim_count": concrete_evidence_claim_count(evidence_claims),
        "residual_risk": residual_risk,
        "artifact_refs": list(request.handoff.get("artifact_refs") or []),
    }


def _related_evidence_ids(output: dict, *, current_evidence_id: str) -> list[str]:
    related_evidence_ids = unique_string_list(output.get("evidence_refs"))
    for coverage_result in list(output.get("coverage_results") or []):
        if isinstance(coverage_result, dict):
            related_evidence_ids.extend(unique_string_list(coverage_result.get("evidence_refs")))
    return list(dict.fromkeys(item for item in related_evidence_ids if item != current_evidence_id))


def _apply_control_context(
    control: dict,
    *,
    claim: str,
    verifies: list[str],
    related_evidence_ids: list[str],
) -> tuple[str, list[str], list[str]]:
    signal = str(control.get("signal") or "").strip()
    reason = clean_text(control.get("reason")) or f"Workflow control `{signal or 'control'}` ran."
    trigger_refs = string_list(control.get("trigger_evidence_refs"))
    return (
        f"{reason} {claim}".strip(),
        list(dict.fromkeys([f"control:{signal}", *verifies]))[:20],
        list(dict.fromkeys([*trigger_refs, *related_evidence_ids]))[:20],
    )


def _evidence_method(archetype: str) -> str:
    return {
        "builder": "implementation_handoff",
        "inspector": "inspection",
        "gatekeeper": "gatekeeper_verdict",
        "guide": "stagnation_guidance",
        "custom": "supporting_observation",
    }.get(archetype, "workflow_handoff")


def _evidence_kind(archetype: str) -> str:
    return {
        "builder": "handoff",
        "inspector": "inspection",
        "gatekeeper": "verdict",
        "guide": "advisory",
        "custom": "observation",
    }.get(archetype, "observation")


def _evidence_source(archetype: str) -> str:
    return {
        "builder": "workspace_change",
        "inspector": "check_execution",
        "gatekeeper": "verdict",
        "guide": "stagnation_analysis",
        "custom": "supporting_role",
    }.get(archetype, "role_output")


def _evidence_verifies(archetype: str, output: dict, *, current_evidence_id: str = "") -> list[str]:
    refs: list[str] = []
    refs.extend(_coverage_result_verify_refs(output.get("coverage_results")))
    if archetype == "inspector":
        for bucket_name in ("check_results", "dynamic_checks"):
            for item in output.get(bucket_name, []) or []:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or item.get("title") or "").strip()
                status = str(item.get("status") or "").strip()
                if item_id:
                    refs.append(f"{bucket_name}:{item_id}:{status or 'unknown'}")
    elif archetype == "gatekeeper":
        refs.extend(f"check:{item}" for item in string_list(output.get("failed_check_ids")))
        measured_evidence = has_measured_gate_evidence(output.get("metric_scores"), output.get("metrics"))
        for item in string_list(output.get("evidence_refs")):
            if item == current_evidence_id and not measured_evidence:
                continue
            refs.append(f"evidence:{item}")
    else:
        refs.extend(string_list(output.get("changed_files")))
        refs.extend(string_list(output.get("observations")))
    return refs[:20]


def _step_result_verify_ref(step_id: object, status: object) -> str:
    cleaned_step = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(step_id))
    cleaned_status = clean_text(status).strip().lower().replace(" ", "_") or "completed"
    return f"step_result:{cleaned_step}:{cleaned_status}"


def _coverage_result_verify_refs(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id or ":" in target_id:
            continue
        status = str(item.get("status") or "unknown").strip() or "unknown"
        refs.append(f"target:{target_id}:{status}")
    return refs


def _evidence_residual_risk(archetype: str, output: dict, handoff: dict) -> str:
    risks: list[str] = []
    risks.extend(string_list(output.get("residual_risks")))
    risks.extend(string_list(output.get("hard_constraint_violations")))
    risks.extend(string_list(output.get("blocking_issues")))
    if archetype == "builder":
        abandoned = clean_text(output.get("abandoned"))
        if abandoned:
            risks.append(abandoned)
    if not risks:
        risks.extend(string_list(handoff.get("blocking_items")))
    if archetype == "gatekeeper" and not risks and output.get("passed") is True:
        return "No blocking residual risk was reported by GateKeeper."
    return "; ".join(risks[:6])
