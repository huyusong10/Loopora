from __future__ import annotations

from loopora.events.step_instruction_payloads import step_instruction_event_payload
from loopora.kernel.step import StepInstruction, StepResult
from loopora.utils import coerced_non_negative_int
from loopora.task_verdict_aliases import canonical_task_verdict_status


def step_instruction_payload(instruction: StepInstruction) -> dict:
    return step_instruction_event_payload(instruction)


def step_planned_payload(instruction: StepInstruction) -> dict:
    return {
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
    }


def step_claimed_payload(instruction: StepInstruction, *, pending_actor: dict) -> dict:
    return {
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "pending_actor": dict(pending_actor),
    }


def step_submitted_payload(result: StepResult) -> dict:
    return {
        "run_id": result.run_id,
        "step_id": result.step_id,
        "iteration": result.iteration,
        "status": result.status.value,
        "summary": result.summary,
        "evidence_claim_count": len(result.evidence_claims),
        "artifact_ref_count": len(result.artifact_refs),
        "blocking_items": list(result.blocking_items),
        "residual_risks": list(result.residual_risks),
    }


def step_committed_payload(
    *,
    run_id: str,
    step_id: str,
    iteration: int,
    result_status: str,
) -> dict:
    return {
        "run_id": run_id,
        "step_id": step_id,
        "iteration": iteration,
        "result_status": result_status,
    }


def strategy_advanced_payload(result: StepResult) -> dict:
    return {
        "run_id": result.run_id,
        "step_id": result.step_id,
        "iteration": result.iteration,
        "result_status": result.status.value,
        "reason": "step_committed",
    }


def evidence_submitted_payload(run_id: str, evidence_entry: dict) -> dict:
    return evidence_accepted_payload(run_id, evidence_entry)


def evidence_accepted_payload(run_id: str, evidence_entry: dict) -> dict:
    artifact_refs = _artifact_ref_payloads(evidence_entry.get("artifact_refs"))
    return {
        "run_id": run_id,
        "evidence_id": str(evidence_entry.get("id") or ""),
        "step_id": str(evidence_entry.get("step_id") or ""),
        "role_id": str(evidence_entry.get("role_id") or ""),
        "archetype": str(evidence_entry.get("archetype") or ""),
        "claim": str(evidence_entry.get("claim") or ""),
        "method": str(evidence_entry.get("method") or ""),
        "result": str(evidence_entry.get("result") or ""),
        "verifies": [str(item) for item in list(evidence_entry.get("verifies") or []) if str(item).strip()],
        "measured_evidence": evidence_entry.get("measured_evidence") is True,
        "artifact_ref_count": len(artifact_refs),
        "artifact_refs": artifact_refs,
        "residual_risk": str(evidence_entry.get("residual_risk") or ""),
    }


def evidence_linked_to_target_payload(run_id: str, evidence_entry: dict) -> dict:
    evidence_id = str(evidence_entry.get("id") or "")
    target_refs = [ref for ref in _verifies_refs(evidence_entry.get("verifies")) if ref.startswith("target:")]
    return {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "target_refs": target_refs,
    }


def coverage_recomputed_payload(run_id: str, coverage: dict) -> dict:
    return {
        "run_id": run_id,
        "status": str(coverage.get("status") or ""),
        "target_count": _coverage_count(coverage, "target_count"),
        "covered_target_count": _coverage_count(coverage, "covered_target_count"),
        "weak_target_count": _coverage_count(coverage, "weak_target_count"),
        "missing_target_count": _coverage_count(coverage, "missing_target_count"),
        "blocked_target_count": _coverage_count(coverage, "blocked_target_count"),
        "top_gaps": [item for item in list(coverage.get("top_gaps") or []) if isinstance(item, dict)][:5],
    }


def verdict_issued_payload(run_id: str, verdict: dict) -> dict:
    payload = {
        "run_id": run_id,
        "status": canonical_task_verdict_status(verdict.get("status")),
        "source": str(verdict.get("source") or ""),
        "summary": str(verdict.get("summary") or ""),
    }
    buckets = _dict_list_payload(verdict.get("buckets"))
    if buckets:
        payload["buckets"] = buckets
    next_gap = _dict_entries(verdict.get("next_gap"))
    if next_gap:
        payload["next_gap"] = next_gap
    return payload


def verdict_requested_payload(run_id: str, verdict: dict) -> dict:
    return {
        "run_id": run_id,
        "requested_status": canonical_task_verdict_status(verdict.get("status")),
    }


def verdict_closure_payload(run_id: str, verdict_payload: dict) -> dict:
    status = canonical_task_verdict_status(verdict_payload.get("status"))
    allowed = status in {"passed", "passed_with_residual_risk"}
    return {
        "run_id": run_id,
        "verdict_status": status,
        "allowed": allowed,
    }


def residual_risk_accepted_payload(run_id: str, verdict_payload: dict) -> dict:
    buckets = verdict_payload.get("buckets") if isinstance(verdict_payload.get("buckets"), dict) else {}
    residual_risk = _dict_entries(buckets.get("residual_risk"))
    return {
        "run_id": run_id,
        "risk_count": len(residual_risk),
        "residual_risk": residual_risk,
    }


def next_gap_selected_payload(run_id: str, verdict_payload: dict) -> dict:
    next_gap = _dict_entries(verdict_payload.get("next_gap"))
    selected_gap = dict(next_gap[0]) if next_gap else {}
    return {
        "run_id": run_id,
        "target_id": str(selected_gap.get("target_id") or ""),
        "status": str(selected_gap.get("status") or ""),
        "next_gap": next_gap,
    }


def iteration_started_payload(*, run_id: str, iteration: int, step_count: int) -> dict:
    return {
        "run_id": run_id,
        "iteration": iteration,
        "step_count": step_count,
    }


def iteration_completed_payload(*, run_id: str, iteration: int, completed_step_count: int, reason: str) -> dict:
    return {
        "run_id": run_id,
        "iteration": iteration,
        "completed_step_count": completed_step_count,
        "reason": reason,
    }


def _dict_list_payload(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, items in value.items():
        if not isinstance(items, list):
            continue
        result[str(key)] = _dict_entries(items)
    return result


def _dict_entries(value: object) -> list[dict]:
    return [dict(item) for item in list(value or []) if isinstance(item, dict)]


def _verifies_refs(value: object) -> list[str]:
    return [str(item).strip() for item in list(value or []) if str(item).strip()]


def _coverage_count(coverage: dict, key: str) -> int:
    return coerced_non_negative_int(coverage.get(key), strict=True, field_name=f"CoverageRecomputed {key}")


def _artifact_ref_payloads(value: object) -> list[dict]:
    refs: list[dict] = []
    for item in list(value or []):
        if not isinstance(item, dict):
            continue
        ref = {
            "kind": str(item.get("kind") or ""),
            "label": str(item.get("label") or ""),
            "uri": str(item.get("uri") or ""),
        }
        content_hash = str(item.get("content_hash") or "")
        if content_hash:
            ref["content_hash"] = content_hash
        created_by_event_id = str(item.get("created_by_event_id") or "")
        if created_by_event_id:
            ref["created_by_event_id"] = created_by_event_id
        refs.append(ref)
    return refs
