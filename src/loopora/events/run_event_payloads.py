from __future__ import annotations

from loopora.events.step_instruction_payloads import step_instruction_event_payload
from loopora.kernel.step import StepInstruction, StepResult


def step_instruction_payload(instruction: StepInstruction) -> dict:
    return step_instruction_event_payload(instruction)


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


def evidence_accepted_payload(run_id: str, evidence_entry: dict) -> dict:
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
        "artifact_ref_count": len([item for item in list(evidence_entry.get("artifact_refs") or []) if isinstance(item, dict)]),
        "residual_risk": str(evidence_entry.get("residual_risk") or ""),
    }


def coverage_recomputed_payload(run_id: str, coverage: dict) -> dict:
    return {
        "run_id": run_id,
        "status": str(coverage.get("status") or ""),
        "target_count": int(coverage.get("target_count") or 0),
        "covered_target_count": int(coverage.get("covered_target_count") or 0),
        "weak_target_count": int(coverage.get("weak_target_count") or 0),
        "missing_target_count": int(coverage.get("missing_target_count") or 0),
        "blocked_target_count": int(coverage.get("blocked_target_count") or 0),
        "top_gaps": [item for item in list(coverage.get("top_gaps") or []) if isinstance(item, dict)][:5],
    }


def verdict_issued_payload(run_id: str, verdict: dict) -> dict:
    payload = {
        "run_id": run_id,
        "status": str(verdict.get("status") or "not_evaluated"),
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
