from __future__ import annotations

from typing import Any

from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset


def _rule_text(asset_ref: str) -> str:
    return load_system_prompt_asset(asset_ref).strip()


def agent_native_todo_contract(*, step_id: str, target_agent: str) -> dict[str, Any]:
    step_text = str(step_id or "").strip() or "current_step"
    target_text = str(target_agent or "").strip() or "the role agent"
    return {
        "recommended": True,
        "not_evidence": True,
        "host_policy": load_system_prompt_asset("agent_native/native-todo-host-policy.md").strip(),
        "items": [
            render_system_prompt_asset("agent_native/native-todo-read-step.md", {"step_id": step_text}).strip(),
            render_system_prompt_asset("agent_native/native-todo-invoke-role.md", {"target_agent": target_text}).strip(),
            load_system_prompt_asset("agent_native/native-todo-fill-template.md").strip(),
            load_system_prompt_asset("agent_native/native-todo-submit-result.md").strip(),
        ],
    }


def agent_native_evidence_rules(archetype: str) -> list[dict[str, str]]:
    base_rules = [
        {
            "id": "evidence_refs.must_be_exact_known_ids",
            "severity": "hard",
            "rule": _rule_text("agent_native/evidence-rule-known-evidence-refs.md"),
        },
        {
            "id": "coverage_results.status_uses_coverage_vocabulary",
            "severity": "hard",
            "rule": _rule_text("agent_native/evidence-rule-coverage-status-vocabulary.md"),
        },
        {
            "id": "coverage_results.target_id_must_be_known_coverage_target",
            "severity": "hard",
            "rule": _rule_text("agent_native/evidence-rule-known-coverage-targets.md"),
        },
    ]
    if archetype == "inspector":
        return [
            *base_rules,
            {
                "id": "inspector.coverage_requires_current_evidence",
                "severity": "hard",
                "rule": _rule_text("agent_native/evidence-rule-inspector-current-evidence.md"),
            },
            {
                "id": "inspector.no_future_terminal_claim",
                "severity": "hard",
                "rule": _rule_text("agent_native/evidence-rule-inspector-no-future-terminal.md"),
            },
        ]
    if archetype == "gatekeeper":
        return [
            *base_rules,
            {
                "id": "gatekeeper.pass_requires_supporting_upstream_evidence",
                "severity": "hard",
                "rule": _rule_text("agent_native/evidence-rule-gatekeeper-supporting-upstream.md"),
            },
            {
                "id": "gatekeeper.blocked_refs_do_not_support_pass",
                "severity": "hard",
                "rule": _rule_text("agent_native/evidence-rule-gatekeeper-blocked-refs.md"),
            },
            {
                "id": "gatekeeper.finish_coverage_is_core_derived",
                "severity": "hard",
                "rule": _rule_text("agent_native/evidence-rule-gatekeeper-finish-coverage.md"),
            },
        ]
    if archetype == "builder":
        return [
            *base_rules,
            {
                "id": "builder.proof_artifacts_strengthen_evidence",
                "severity": "advisory",
                "rule": _rule_text("agent_native/evidence-rule-builder-proof-artifacts.md"),
            },
        ]
    return base_rules
