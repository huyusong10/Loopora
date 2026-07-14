from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import (
    _replace_dispute_chargeback_visible_scaffold,
)
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_dispute_chargeback_lifecycle_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = _dedupe_values(projection.evidence_verifies)
    gatekeeper_verifies = _dedupe_values(
        [
            "done_when",
            "fake_done",
            "evidence_buckets",
            "residual_risk",
            "dispute-chargeback",
            "webhook-ordering",
            "provider-contract",
            "evidence-deadline",
            "reason-code",
            "ledger-reconciliation",
            "payout-settlement",
            "payment-refund-billing",
            "message-delivery",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    contract_verifies = _dedupe_values(
        [
            "dispute-chargeback",
            "webhook-ordering",
            "provider-contract",
            "evidence-deadline",
            "reason-code",
            "payment-refund-billing",
            "ledger-reconciliation",
            "payout-settlement",
            "message-delivery",
            "audit-log",
            "monitoring",
            "privacy-redaction",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    dispute_evidence_verifies = _dedupe_values(
        [
            "dispute-chargeback",
            "webhook-ordering",
            "provider-contract",
            "evidence-deadline",
            "reason-code",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection_verifies,
        ]
    )
    ledger_notification_verifies = _dedupe_values(
        [
            "dispute-chargeback",
            "ledger-reconciliation",
            "payout-settlement",
            "payment-refund-billing",
            "message-delivery",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "dispute-chargeback-contract-parallel-lifecycle"
    workflow_intents._replace_dispute_chargeback_lifecycle_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "dispute_contract_inspector", "role_definition_key": "dispute-contract-inspector"},
        {"id": "chargeback_lifecycle_builder", "role_definition_key": "chargeback-lifecycle-builder"},
        {"id": "dispute_evidence_inspector", "role_definition_key": "dispute-evidence-inspector"},
        {"id": "ledger_notification_inspector", "role_definition_key": "ledger-notification-inspector"},
        {"id": "dispute_chargeback_gatekeeper", "role_definition_key": "dispute-chargeback-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "dispute_contract_inspection_step",
            "role_id": "dispute_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 32}},
            "on_pass": "continue",
        },
        {
            "id": "chargeback_lifecycle_builder_step",
            "role_id": "chargeback_lifecycle_builder",
            "inputs": {"handoffs_from": ["dispute_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "dispute_evidence_inspection_step",
            "role_id": "dispute_evidence_inspector",
            "parallel_group": "dispute_chargeback_review_pack",
            "inputs": {
                "handoffs_from": ["dispute_contract_inspection_step", "chargeback_lifecycle_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": dispute_evidence_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "ledger_notification_inspection_step",
            "role_id": "ledger_notification_inspector",
            "parallel_group": "dispute_chargeback_review_pack",
            "inputs": {
                "handoffs_from": ["dispute_contract_inspection_step", "chargeback_lifecycle_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": ledger_notification_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "dispute_chargeback_gatekeeper_step",
            "role_id": "dispute_chargeback_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "dispute_contract_inspection_step",
                    "chargeback_lifecycle_builder_step",
                    "dispute_evidence_inspection_step",
                    "ledger_notification_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
    _replace_dispute_chargeback_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )
