from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_usage_quota_metering_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "quota-metering",
            "idempotency",
            "permission-auth",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    race_verifies = _dedupe_values(
        [
            "quota-metering",
            "idempotency",
            "conflict-resolution",
            "permission-auth",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    reconciliation_verifies = _dedupe_values(
        [
            "quota-metering",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    gatekeeper_verifies = _dedupe_values(
        [
            "done_when",
            "fake_done",
            "evidence_buckets",
            "residual_risk",
            "quota-metering",
            "idempotency",
            "conflict-resolution",
            "permission-auth",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "usage-quota-contract-parallel-metering"
    workflow_intents._replace_usage_quota_metering_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "quota_contract_inspector", "role_definition_key": "quota-contract-inspector"},
        {"id": "usage_metering_builder", "role_definition_key": "usage-metering-builder"},
        {"id": "quota_race_inspector", "role_definition_key": "quota-race-inspector"},
        {"id": "billing_reconciliation_inspector", "role_definition_key": "billing-reconciliation-inspector"},
        {"id": "usage_quota_gatekeeper", "role_definition_key": "usage-quota-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "quota_contract_inspection_step", "role_id": "quota_contract_inspector", "on_pass": "continue"},
        {
            "id": "usage_metering_builder_step",
            "role_id": "usage_metering_builder",
            "inputs": {
                "handoffs_from": ["quota_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "quota_race_inspection_step",
            "role_id": "quota_race_inspector",
            "parallel_group": "usage_quota_review_pack",
            "inputs": {
                "handoffs_from": ["quota_contract_inspection_step", "usage_metering_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": race_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "billing_reconciliation_inspection_step",
            "role_id": "billing_reconciliation_inspector",
            "parallel_group": "usage_quota_review_pack",
            "inputs": {
                "handoffs_from": ["quota_contract_inspection_step", "usage_metering_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": reconciliation_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "usage_quota_gatekeeper_step",
            "role_id": "usage_quota_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "quota_contract_inspection_step",
                    "usage_metering_builder_step",
                    "quota_race_inspection_step",
                    "billing_reconciliation_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
