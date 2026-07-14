from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import (
    _replace_payout_settlement_visible_scaffold,
)
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_payout_settlement_reconciliation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify not in {"kyc-aml-screening", "dispute-chargeback", "message-delivery"}]
    contract_verifies = _dedupe_values(
        [
            "payout-settlement",
            "ledger-reconciliation",
            "payment-refund-billing",
            "payout-batch-cutoff",
            "provider-contract",
            "provider-bank-reconciliation",
            "idempotency",
            "double-payout",
            "tenant-isolation",
            "permission-auth",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    settlement_verifies = _dedupe_values(
        [
            "payout-settlement",
            "ledger-reconciliation",
            "payment-refund-billing",
            "payout-batch-cutoff",
            "provider-contract",
            "provider-bank-reconciliation",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    access_idempotency_verifies = _dedupe_values(
        [
            "payout-settlement",
            "idempotency",
            "double-payout",
            "kyc-hold",
            "tenant-isolation",
            "permission-auth",
            "audit-log",
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
            "payout-settlement",
            "ledger-reconciliation",
            "payment-refund-billing",
            "payout-batch-cutoff",
            "provider-contract",
            "provider-bank-reconciliation",
            "idempotency",
            "double-payout",
            "kyc-hold",
            "tenant-isolation",
            "permission-auth",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "payout-settlement-contract-parallel-reconciliation"
    workflow_intents._replace_payout_settlement_reconciliation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "payout_contract_inspector", "role_definition_key": "payout-contract-inspector"},
        {"id": "payout_settlement_builder", "role_definition_key": "payout-settlement-builder"},
        {"id": "settlement_reconciliation_inspector", "role_definition_key": "settlement-reconciliation-inspector"},
        {"id": "access_idempotency_inspector", "role_definition_key": "access-idempotency-inspector"},
        {"id": "payout_settlement_gatekeeper", "role_definition_key": "payout-settlement-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "payout_contract_inspection_step",
            "role_id": "payout_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "payout_settlement_builder_step",
            "role_id": "payout_settlement_builder",
            "inputs": {"handoffs_from": ["payout_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "settlement_reconciliation_inspection_step",
            "role_id": "settlement_reconciliation_inspector",
            "parallel_group": "payout_settlement_review_pack",
            "inputs": {
                "handoffs_from": ["payout_contract_inspection_step", "payout_settlement_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": settlement_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "access_idempotency_inspection_step",
            "role_id": "access_idempotency_inspector",
            "parallel_group": "payout_settlement_review_pack",
            "inputs": {
                "handoffs_from": ["payout_contract_inspection_step", "payout_settlement_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": access_idempotency_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "payout_settlement_gatekeeper_step",
            "role_id": "payout_settlement_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "payout_contract_inspection_step",
                    "payout_settlement_builder_step",
                    "settlement_reconciliation_inspection_step",
                    "access_idempotency_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
    _replace_payout_settlement_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )
