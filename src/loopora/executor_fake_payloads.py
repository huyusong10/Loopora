from __future__ import annotations

from loopora.branding import APP_STATE_DIRNAME
from loopora.executor_alignment_bundle_fixtures import (
    alignment_bundle_yaml,
    alignment_bundle_yaml_with_governance_markers_listed_as_facts,
    alignment_bundle_yaml_with_lineage_metadata,
    alignment_bundle_yaml_with_unsupported_observed_workdir_claim,
    alignment_bundle_yaml_without_semantics,
    alignment_chinese_bundle_yaml,
    alignment_chinese_bundle_yaml_with_english_visible_names,
    alignment_chinese_improvement_bundle_yaml,
    alignment_chinese_refund_repair_bundle_yaml,
    alignment_improvement_bundle_yaml,
    alignment_refund_repair_bundle_yaml,
)
from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response,
    alignment_chinese_agreement_response,
    alignment_chinese_improvement_agreement_response,
    alignment_chinese_refund_agreement_response,
    alignment_improvement_agreement_response,
    alignment_refund_agreement_response,
)
from loopora.executor_alignment_payloads import build_alignment_payload
from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence,
    alignment_readiness_evidence,
)
from loopora.executor_alignment_responses import (
    alignment_default_bundle_response,
    alignment_response,
)
from loopora.executor_alignment_payloads import FakePayloadError

from dataclasses import dataclass

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


"""Fake Builder, Check Planner, and Inspector role payloads."""

def fake_builder_payload(iter_id: int) -> dict:
    return {
        "attempted": f"Iter {iter_id}: refine workdir against the frozen task contract",
        "abandoned": "Did not widen scope or lower Done When to make the iteration look complete.",
        "assumption": "The highest-impact gain is still the primary path with evidence Inspector can verify.",
        "summary": "Applied a focused change strategy and left the proof surface for Inspector and GateKeeper.",
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }

def fake_check_planner_payload(compiled_spec: dict) -> dict:
    goal = (compiled_spec.get("goal") or "the prototype").strip()
    return {
        "checks": [
            {
                "title": "Goal alignment",
                "details": (
                    f"When: someone reviews the current prototype against the goal.\n"
                    f"Expect: the main flow clearly moves toward {goal}.\n"
                    "Fail if: the prototype feels unrelated, confusing, or incomplete in its primary direction."
                ),
                "when": "Someone evaluates the prototype as-is.",
                "expect": f"The main flow visibly supports {goal}.",
                "fail_if": "The current direction is confusing or disconnected from the goal.",
            },
            {
                "title": "Primary interaction holds together",
                "details": (
                    "When: a user follows the most obvious interaction path.\n"
                    "Expect: the path remains understandable from start to finish.\n"
                    "Fail if: the experience breaks, stalls, or loses its state."
                ),
                "when": "A user follows the most obvious path.",
                "expect": "The path stays understandable and coherent.",
                "fail_if": "The experience breaks, stalls, or loses its state.",
            },
            {
                "title": "Prototype safety",
                "details": (
                    "When: the user hits an incomplete or awkward edge in the prototype.\n"
                    "Expect: the interface still communicates what is happening.\n"
                    "Fail if: the prototype crashes, misleads the user, or becomes unusable."
                ),
                "when": "An incomplete or awkward edge appears.",
                "expect": "The interface still communicates clearly.",
                "fail_if": "The prototype crashes, misleads the user, or becomes unusable.",
            },
        ],
        "generation_notes": "Generated a compact exploratory check set because the spec did not provide explicit checks.",
    }

def fake_tester_payload(iter_id: int, checks: list[dict], check_count: int) -> dict:
    passed_checks = min(check_count, 1 + iter_id)
    total_checks = check_count
    results = []
    for index, check in enumerate(checks, start=1):
        status = "passed" if index <= passed_checks else "failed"
        results.append(
            {
                "id": check["id"],
                "title": check["title"],
                "status": status,
                "notes": _fake_check_notes(check, status),
            }
        )
    return {
        "execution_summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": max(total_checks - passed_checks, 0),
            "errored": 0,
            "total_duration_ms": 500 + iter_id * 25,
        },
        "check_results": results,
        "dynamic_checks": [],
        "tester_observations": (
            "Fake executor evaluated the compiled Markdown checks against the frozen run contract; "
            "passed checks move toward Proven only through traceable evidence, while failed checks stay "
            "Blocking or Unproven for GateKeeper."
        ),
        "coverage_results": [],
    }

def _fake_check_notes(check: dict, status: str) -> str:
    base = str(check.get("expect") or check.get("details") or "").strip()
    if status == "passed":
        suffix = "Fake evidence treats this as Proven only through the inspector evidence ledger."
    else:
        suffix = "This remains Blocking or Unproven until a later Builder repair produces new proof."
    return f"{base} {suffix}".strip()

@dataclass(frozen=True)
class FakePayloadContext:
    iter_id: int
    compiled_spec: dict
    checks: list[dict]
    check_count: int
    archetype: str

def fake_payload_context(request) -> FakePayloadContext:
    compiled_spec = request.extra_context.get("compiled_spec", {})
    checks = compiled_spec.get("checks", [])
    return FakePayloadContext(
        iter_id=int(request.extra_context.get("iter_id", 0)),
        compiled_spec=compiled_spec,
        checks=checks,
        check_count=max(len(checks), 1),
        archetype=str(request.role_archetype or request.extra_context.get("archetype") or request.role).strip().lower(),
    )

def fake_provider_failure_message(scenario: str, request, context: FakePayloadContext) -> str:
    if scenario == "alignment_resume_failure" and request.role == "alignment" and request.resume_session_id:
        return "simulated native resume failure"
    if scenario == "role_failure" and context.archetype in {"tester", "inspector"}:
        return "simulated inspector failure"
    return ""

def fake_role_payload(scenario: str, request, context: FakePayloadContext) -> dict | None:
    if context.archetype in {"generator", "builder"}:
        payload = fake_builder_payload(context.iter_id)
    elif request.role == "check_planner":
        payload = fake_check_planner_payload(context.compiled_spec)
    elif context.archetype in {"tester", "inspector"}:
        payload = fake_tester_payload(context.iter_id, context.checks, context.check_count)
    elif context.archetype in {"verifier", "gatekeeper"}:
        payload = fake_verifier_payload(scenario, context.iter_id, request, context.check_count)
    elif context.archetype in {"challenger", "guide"}:
        payload = fake_challenger_payload(context.iter_id, request)
    elif context.archetype == "custom":
        payload = fake_custom_payload()
    else:
        payload = None
    return payload


__all__ = (
    "FakePayloadError",
    "alignment_agreement_response",
    "alignment_bundle_yaml",
    "alignment_bundle_yaml_with_governance_markers_listed_as_facts",
    "alignment_bundle_yaml_with_lineage_metadata",
    "alignment_bundle_yaml_with_unsupported_observed_workdir_claim",
    "alignment_bundle_yaml_without_semantics",
    "alignment_chinese_agreement_response",
    "alignment_chinese_bundle_yaml",
    "alignment_chinese_bundle_yaml_with_english_visible_names",
    "alignment_chinese_improvement_agreement_response",
    "alignment_chinese_improvement_bundle_yaml",
    "alignment_chinese_improvement_readiness_evidence",
    "alignment_chinese_readiness_evidence",
    "alignment_chinese_refund_agreement_response",
    "alignment_chinese_refund_repair_bundle_yaml",
    "alignment_default_bundle_response",
    "alignment_improvement_agreement_response",
    "alignment_improvement_bundle_yaml",
    "alignment_improvement_readiness_evidence",
    "alignment_readiness_evidence",
    "alignment_refund_agreement_response",
    "alignment_refund_repair_bundle_yaml",
    "alignment_response",
    "build_alignment_payload",
    "build_fake_payload",
)


def build_fake_payload(scenario: str, request) -> dict:
    context = fake_payload_context(request)
    _raise_for_fake_provider_failure(scenario, request, context)
    if request.role == "alignment" or context.archetype == "alignment":
        return build_alignment_payload(scenario, request)
    if _should_destructively_clear_workdir(scenario, context.archetype):
        _clear_workdir_for_destructive_fake(request)
    payload = fake_role_payload(scenario, request, context)
    if payload is None:
        raise FakePayloadError(f"unsupported fake role: {request.role}")
    return payload


def _raise_for_fake_provider_failure(scenario: str, request, context: FakePayloadContext) -> None:
    message = fake_provider_failure_message(scenario, request, context)
    if message:
        raise FakePayloadError(message)


def _should_destructively_clear_workdir(scenario: str, archetype: str) -> bool:
    return (scenario == "destructive_generator" and archetype in {"generator", "builder"}) or (
        scenario == "destructive_tester" and archetype in {"tester", "inspector"}
    )


def _clear_workdir_for_destructive_fake(request) -> None:
    for child in request.workdir.iterdir():
        if child.name == APP_STATE_DIRNAME:
            continue
        if child.is_dir():
            for nested in sorted(child.rglob("*"), key=lambda path: len(path.parts), reverse=True):
                if nested.is_file():
                    nested.unlink()
                elif nested.is_dir():
                    nested.rmdir()
            child.rmdir()
        else:
            child.unlink()
