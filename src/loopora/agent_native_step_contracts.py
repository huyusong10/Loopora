from __future__ import annotations

from typing import Any


def agent_native_todo_contract(*, step_id: str, target_agent: str) -> dict[str, Any]:
    step_text = str(step_id or "").strip() or "current_step"
    target_text = str(target_agent or "").strip() or "the role agent"
    return {
        "recommended": True,
        "not_evidence": True,
        "host_policy": (
            "Create or update the host's official todo/progress-list when available; otherwise continue with "
            "the step contract and result template. Todo state is user-visible progress only, not Loopora evidence."
        ),
        "items": [
            f"Read agent_v3_envelope.summary and the step contract for {step_text}.",
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
