from __future__ import annotations

from typing import Any

from loopora.run_takeaways import build_judgment_contract
from loopora.service_agent_native_contracts import (
    _agent_native_actionable_blocking_item,
    _agent_native_actionable_repair_next_action,
    _agent_native_current_gap_repair_next_action,
    _agent_native_previous_blocked_handoff,
    _agent_native_repair_blockers_still_current,
    _agent_native_role_posture_list,
    _agent_native_string_list,
)
from loopora.structured_numbers import structured_non_negative_int


def agent_native_capsule_continuation_context(context_packet: object) -> dict[str, Any]:
    packet = context_packet if isinstance(context_packet, dict) else {}
    continuation = packet.get("continuation") if isinstance(packet.get("continuation"), dict) else {}
    return dict(continuation) if continuation.get("active") is True else {}


def agent_native_capsule_iteration_repair_context(context_packet: object) -> dict[str, Any]:
    packet = context_packet if isinstance(context_packet, dict) else {}
    iteration = packet.get("iteration") if isinstance(packet.get("iteration"), dict) else {}
    previous_summary = packet.get("upstream", {}).get("previous_iteration_summary") if isinstance(packet.get("upstream"), dict) else None
    previous_summary = previous_summary if isinstance(previous_summary, dict) else {}
    iter_index = structured_non_negative_int(iteration.get("iter_index"))
    if not previous_summary and not (iter_index and iter_index > 0):
        return {}
    blocked_handoff = _agent_native_previous_blocked_handoff(previous_summary)
    gatekeeper_verdict = previous_summary.get("gatekeeper_verdict") if isinstance(previous_summary.get("gatekeeper_verdict"), dict) else {}
    blocking_items = _agent_native_string_list(blocked_handoff.get("blocking_items"))
    if not blocking_items:
        blocking_items = _agent_native_string_list(gatekeeper_verdict.get("blocking_issues"))
    blocking_items = [_agent_native_actionable_blocking_item(item) for item in blocking_items if item]
    top_gaps = [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5]
    summary = str(blocked_handoff.get("summary") or gatekeeper_verdict.get("decision_summary") or "").strip()
    recommended_next_action = str(
        blocked_handoff.get("recommended_next_action")
        or gatekeeper_verdict.get("feedback_to_builder")
        or gatekeeper_verdict.get("feedback_to_generator")
        or ""
    ).strip()
    if not _agent_native_repair_blockers_still_current(blocking_items, top_gaps):
        blocking_items = []
        recommended_next_action = _agent_native_current_gap_repair_next_action(top_gaps)
    recommended_next_action = _agent_native_actionable_repair_next_action(recommended_next_action, blocking_items)
    if not any((blocking_items, top_gaps, summary, recommended_next_action)):
        return {}
    source = blocked_handoff.get("source") if isinstance(blocked_handoff.get("source"), dict) else {}
    return {
        "active": True,
        "previous_iteration": structured_non_negative_int(previous_summary.get("iter")),
        "source_step_id": str(source.get("step_id") or "").strip(),
        "source_role": str(source.get("role_name") or source.get("role_id") or "").strip(),
        "status": str(blocked_handoff.get("status") or "").strip(),
        "summary": summary,
        "blocking_items": blocking_items[:8],
        "recommended_next_action": recommended_next_action,
        "evidence_refs": _agent_native_string_list(blocked_handoff.get("evidence_refs"))[:8],
        "top_gaps": top_gaps,
    }


def agent_native_capsule_judgment_contract(run: dict, context_packet: object) -> dict[str, Any]:
    packet = context_packet if isinstance(context_packet, dict) else {}
    contract = packet.get("contract") if isinstance(packet.get("contract"), dict) else {}
    if not contract:
        return build_judgment_contract(run)
    projection = build_judgment_contract(run)
    contract_role_postures = _agent_native_role_posture_list(contract.get("role_postures"))
    contract_coverage_targets = [dict(item) for item in list(contract.get("coverage_targets") or []) if isinstance(item, dict)]
    projection.update(
        {
            "contract_path": str(contract.get("path") or projection.get("contract_path") or "").strip(),
            "goal": str(contract.get("goal") or projection.get("goal") or "").strip(),
            "constraints": str(contract.get("constraints") or projection.get("constraints") or "").strip(),
            "check_mode": str(contract.get("check_mode") or projection.get("check_mode") or "").strip(),
            "check_count": structured_non_negative_int(contract.get("check_count")),
            "completion_mode": str(contract.get("completion_mode") or projection.get("completion_mode") or "").strip(),
            "collaboration_summary": str(contract.get("collaboration_summary") or projection.get("collaboration_summary") or "").strip(),
            "loop_fit_reasons": _agent_native_string_list(contract.get("loop_fit_reasons")) or projection.get("loop_fit_reasons", []),
            "workflow_preset": str(contract.get("workflow_preset") or projection.get("workflow_preset") or "").strip(),
            "workflow_collaboration_intent": str(
                contract.get("workflow_collaboration_intent") or projection.get("workflow_collaboration_intent") or ""
            ).strip(),
            "judgment_tradeoffs": _agent_native_string_list(contract.get("judgment_tradeoffs")) or projection.get("judgment_tradeoffs", []),
            "execution_strategy": _agent_native_string_list(contract.get("execution_strategy")) or projection.get("execution_strategy", []),
            "local_governance": _agent_native_string_list(contract.get("local_governance")) or projection.get("local_governance", []),
            "role_postures": contract_role_postures or projection.get("role_postures", []),
            "coverage_targets": contract_coverage_targets or projection.get("coverage_targets", []),
            "success_surface": _agent_native_string_list(contract.get("success_surface")) or projection.get("success_surface", []),
            "fake_done_states": _agent_native_string_list(contract.get("fake_done_states")) or projection.get("fake_done_states", []),
            "evidence_preferences": _agent_native_string_list(contract.get("evidence_preferences")) or projection.get("evidence_preferences", []),
            "residual_risk": str(contract.get("residual_risk") or projection.get("residual_risk") or "").strip(),
        }
    )
    return projection


def agent_native_required_coverage(context_packet: dict[str, Any] | None) -> dict[str, Any]:
    packet = context_packet if isinstance(context_packet, dict) else {}
    iteration = packet.get("iteration") if isinstance(packet.get("iteration"), dict) else {}
    return {
        "status": str(iteration.get("coverage_status") or "pending"),
        "evidence_progress_mode": str(iteration.get("evidence_progress_mode") or "none"),
        "covered_check_count": structured_non_negative_int(iteration.get("covered_check_count")),
        "missing_check_count": structured_non_negative_int(iteration.get("missing_check_count")),
        "target_count": structured_non_negative_int(iteration.get("target_count")),
        "covered_target_count": structured_non_negative_int(iteration.get("covered_target_count")),
        "weak_target_count": structured_non_negative_int(iteration.get("weak_target_count")),
        "missing_target_count": structured_non_negative_int(iteration.get("missing_target_count")),
        "blocked_target_count": structured_non_negative_int(iteration.get("blocked_target_count")),
        "covered_check_ids": [str(item) for item in list(iteration.get("covered_check_ids") or []) if str(item).strip()],
        "missing_check_ids": [str(item) for item in list(iteration.get("missing_check_ids") or []) if str(item).strip()],
        "top_gaps": [dict(item) for item in list(iteration.get("coverage_top_gaps") or []) if isinstance(item, dict)][:5],
    }


def agent_native_todo_contract(*, step_id: str, target_agent: str) -> dict[str, Any]:
    step_text = str(step_id or "").strip() or "current_step"
    target_text = str(target_agent or "").strip() or "the role agent"
    return {
        "recommended": True,
        "not_evidence": True,
        "host_policy": (
            "Create or update the host's official todo/progress-list when available; otherwise continue with "
            "the capsule and result template. Todo state is user-visible progress only, not Loopora evidence."
        ),
        "items": [
            f"Read agent_v3_envelope.summary and capsule for {step_text}.",
            f"Invoke {target_text} through the host's official subagent/task mechanism.",
            "Fill the provided result template without changing Loopora's frozen contract fields.",
            "Submit the filled result and read agent_v3_envelope.summary before deciding whether the task is proven.",
        ],
    }


def agent_native_evidence_rules(archetype: str) -> list[dict[str, str]]:
    base_rules = [
        {
            "id": "evidence_refs.must_be_exact_known_ids",
            "severity": "hard",
            "rule": "Every evidence_refs value, including coverage_results evidence_refs, must be copied exactly from known_evidence_ids. Do not invent, suffix, split, or derive new evidence IDs.",
        },
        {
            "id": "coverage_results.status_uses_coverage_vocabulary",
            "severity": "hard",
            "rule": "coverage_results.status must use coverage vocabulary such as covered, weak, blocked, or missing; keep Proven, Weak, Unproven, Blocking, and Residual risk as verdict buckets or notes.",
        },
        {
            "id": "coverage_results.target_id_must_be_known_coverage_target",
            "severity": "hard",
            "rule": "Every coverage_results.target_id must be copied exactly from loopora_result_contract.coverage_target_ids or active judgment_contract.coverage_targets[].id; do not invent or rename coverage target IDs.",
        },
    ]
    if archetype == "inspector":
        return [
            *base_rules,
            {
                "id": "inspector.coverage_requires_current_evidence",
                "severity": "hard",
                "rule": "Mark coverage passed only when current upstream evidence already proves it.",
            },
            {
                "id": "inspector.no_future_terminal_claim",
                "severity": "hard",
                "rule": "Do not mark a future terminal run state as passed before GateKeeper has completed.",
            },
        ]
    if archetype == "gatekeeper":
        return [
            *base_rules,
            {
                "id": "gatekeeper.pass_requires_supporting_upstream_evidence",
                "severity": "hard",
                "rule": "A pass must cite supporting upstream evidence_refs from known_evidence_ids.",
            },
            {
                "id": "gatekeeper.blocked_refs_do_not_support_pass",
                "severity": "hard",
                "rule": "Evidence from blocked, failed, rejected, or errored steps cannot support a pass.",
            },
            {
                "id": "gatekeeper.finish_coverage_is_core_derived",
                "severity": "hard",
                "rule": "Do not add a passed gatekeeper.finish coverage row; Loopora Core derives finish coverage from the submitted verdict.",
            },
        ]
    if archetype == "builder":
        return [
            *base_rules,
            {
                "id": "builder.proof_artifacts_strengthen_evidence",
                "severity": "advisory",
                "rule": "When possible, include concrete proof_files or proof_artifacts so downstream GateKeeper evidence is supportable.",
            },
        ]
    return base_rules
