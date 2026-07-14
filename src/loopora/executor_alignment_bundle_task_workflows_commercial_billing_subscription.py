from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_subscription_entitlement_billing_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify
        for verify in projection.evidence_verifies
        if verify
        not in {
            "subscription-deliverability",
            "message-delivery",
            "tax-compliance",
            "webhook-ordering",
        }
    ]
    contract_verifies = _dedupe_values(
        [
            "subscription-entitlement",
            "payment-refund-billing",
            "ledger-reconciliation",
            "provider-contract",
            "eval-set",
            "idempotency",
            "retry-timeout",
            "permission-auth",
            "tenant-isolation",
            "quota-metering",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    entitlement_verifies = _dedupe_values(
        [
            "subscription-entitlement",
            "eval-set",
            "permission-auth",
            "tenant-isolation",
            "quota-metering",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    billing_verifies = _dedupe_values(
        [
            "subscription-entitlement",
            "payment-refund-billing",
            "ledger-reconciliation",
            "provider-contract",
            "eval-set",
            "idempotency",
            "retry-timeout",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    gatekeeper_verifies = _dedupe_values(
        [
            "done_when",
            "fake_done",
            "evidence_buckets",
            "residual_risk",
            "subscription-entitlement",
            "payment-refund-billing",
            "ledger-reconciliation",
            "provider-contract",
            "eval-set",
            "idempotency",
            "retry-timeout",
            "permission-auth",
            "tenant-isolation",
            "quota-metering",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "subscription-entitlement-contract-parallel-billing"
    workflow_intents._replace_subscription_entitlement_billing_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "subscription_contract_inspector", "role_definition_key": "subscription-contract-inspector"},
        {"id": "entitlement_billing_builder", "role_definition_key": "entitlement-billing-builder"},
        {"id": "entitlement_state_inspector", "role_definition_key": "entitlement-state-inspector"},
        {
            "id": "billing_proration_reconciliation_inspector",
            "role_definition_key": "billing-proration-reconciliation-inspector",
        },
        {"id": "subscription_entitlement_gatekeeper", "role_definition_key": "subscription-entitlement-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "subscription_contract_inspection_step",
            "role_id": "subscription_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "entitlement_billing_builder_step",
            "role_id": "entitlement_billing_builder",
            "inputs": {
                "handoffs_from": ["subscription_contract_inspection_step"],
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "entitlement_state_inspection_step",
            "role_id": "entitlement_state_inspector",
            "parallel_group": "subscription_entitlement_review_pack",
            "inputs": {
                "handoffs_from": ["subscription_contract_inspection_step", "entitlement_billing_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": entitlement_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "billing_proration_reconciliation_inspection_step",
            "role_id": "billing_proration_reconciliation_inspector",
            "parallel_group": "subscription_entitlement_review_pack",
            "inputs": {
                "handoffs_from": ["subscription_contract_inspection_step", "entitlement_billing_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": billing_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "subscription_entitlement_gatekeeper_step",
            "role_id": "subscription_entitlement_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "subscription_contract_inspection_step",
                    "entitlement_billing_builder_step",
                    "entitlement_state_inspection_step",
                    "billing_proration_reconciliation_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
