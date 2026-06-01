from __future__ import annotations

"""Fake GateKeeper, Guide, and Custom role payloads."""

from loopora.step_instruction_context import step_instruction_context_from_mapping


def fake_verifier_payload(scenario: str, iter_id: int, request, check_count: int) -> dict:
    tester_output = (
        request.extra_context.get("inspector_output")
        or request.extra_context.get("tester_output")
        or {
            "execution_summary": {"total_checks": check_count, "passed": 0},
            "check_results": [],
        }
    )
    total_checks = max(tester_output["execution_summary"]["total_checks"], 1)
    passed_checks = tester_output["execution_summary"]["passed"]
    composite = (
        0.62
        if scenario == "plateau" and iter_id < 2
        else 0.621
        if scenario == "plateau"
        else round(min(0.45 + iter_id * 0.25, 1.0), 3)
    )
    failed_check_ids = [check["id"] for check in tester_output["check_results"] if check.get("status") != "passed"]
    check_pass_rate = round(passed_checks / total_checks, 3)
    passed = composite >= 0.9 and not failed_check_ids
    evidence_refs = _evidence_refs(request)
    evidence_claims = _fake_gatekeeper_evidence_claims(
        passed=passed,
        evidence_refs=evidence_refs,
        failed_check_ids=failed_check_ids,
    )
    return {
        "passed": passed,
        "decision_summary": (
            "Task verdict passes from upstream evidence refs; the run lifecycle alone is not proof."
            if passed
            else "Task verdict is not ready because Weak, Unproven, or Blocking evidence remains."
        ),
        "composite_score": composite,
        "metrics": [
            {
                "name": "check_pass_rate",
                "value": check_pass_rate,
                "threshold": 0.9,
                "passed": check_pass_rate >= 0.9,
            },
            {
                "name": "quality_score",
                "value": composite,
                "threshold": 0.9,
                "passed": composite >= 0.9,
            },
        ],
        "metric_scores": {
            "check_pass_rate": {
                "value": check_pass_rate,
                "threshold": 0.9,
                "passed": check_pass_rate >= 0.9,
            },
            "quality_score": {
                "value": composite,
                "threshold": 0.9,
                "passed": composite >= 0.9,
            },
        },
        "blocking_issues": [],
        "hard_constraint_violations": [],
        "failed_check_ids": failed_check_ids,
        "priority_failures": [],
        "feedback_to_builder": "Repair the smallest Blocking or Unproven gap without lowering the frozen contract.",
        "feedback_to_generator": "Repair the smallest Blocking or Unproven gap without lowering the frozen contract.",
        "evidence_refs": evidence_refs if passed else [],
        "evidence_claims": evidence_claims,
        "residual_risks": [],
        "coverage_results": [],
    }


def fake_challenger_payload(iter_id: int, request) -> dict:
    return {
        "created_at_iter": iter_id,
        "mode": request.extra_context.get("stagnation_mode", "plateau"),
        "consumed": False,
        "analysis": {
            "stagnation_pattern": "fake executor detected stalled gains with Weak or Unproven evidence.",
            "recommended_shift": "Try the smallest repair or proof that turns one Blocking or Unproven gap into Proven evidence.",
            "risk_note": "Changing direction too broadly may hide Residual risk or silently lower the frozen contract.",
        },
        "seed_question": "What is the smallest testable change that breaks the plateau?",
        "meta_note": "This is a suggestion, not a command.",
    }


def fake_custom_payload() -> dict:
    return {
        "status": "advisory",
        "summary": "Collected read-only evidence against the frozen contract and prepared a scoped handoff.",
        "blocking_items": [
            "A restricted role can guide the next move but cannot close the loop alone.",
        ],
        "recommended_next_action": "Use the strongest evidence path for the next change without lowering Done When.",
        "observations": [
            "The custom role stayed inside the current workspace evidence.",
            "No write action was claimed from this restricted role.",
        ],
        "recommendations": [
            "Use the strongest evidence path for the next change without lowering Done When.",
        ],
        "risks": [
            "A restricted role can guide the next move but cannot close the loop alone.",
        ],
        "handoff_note": "Pass these observations to a Builder or Inspector step.",
    }


def _fake_gatekeeper_evidence_claims(
    *,
    passed: bool,
    evidence_refs: list[str],
    failed_check_ids: list[str],
) -> list[str]:
    if passed:
        joined_refs = ", ".join(evidence_refs) if evidence_refs else "measured gate metrics"
        return [(f"Proven: GateKeeper cited upstream evidence refs ({joined_refs}) and kept run status separate from task verdict.")]
    if failed_check_ids:
        joined_checks = ", ".join(failed_check_ids[:4])
        return [(f"Blocking: compiled checks remain unpassed ({joined_checks}), so the task contract cannot be lowered to close the run.")]
    return ["Unproven: quality evidence is still below the GateKeeper threshold."]


def _evidence_refs(request) -> list[str]:
    step_instruction_context = step_instruction_context_from_mapping(request.extra_context)
    evidence_items = []
    if isinstance(step_instruction_context, dict):
        evidence_items = list((step_instruction_context.get("evidence") or {}).get("items") or [])
    return [
        str(item.get("id"))
        for item in evidence_items
        if isinstance(item, dict) and str(item.get("id") or "").strip() and str(item.get("archetype") or "").strip().lower() != "gatekeeper"
    ][-3:]
