from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_payment_webhook_ledger_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "webhook-ordering",
            "provider-contract",
            "eval-set",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "ledger-reconciliation",
            "dispute-chargeback",
            "payout-settlement",
            "payment-refund-billing",
            "session-lifecycle",
            "data-export",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    webhook_verifies = _dedupe_values(
        [
            "webhook-ordering",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "session-lifecycle",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    ledger_verifies = _dedupe_values(
        [
            "ledger-reconciliation",
            "dispute-chargeback",
            "payout-settlement",
            "payment-refund-billing",
            "idempotency",
            "data-export",
            "audit-log",
            "privacy-redaction",
            "monitoring",
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
            "webhook-ordering",
            "ledger-reconciliation",
            "payout-settlement",
            "dispute-chargeback",
            "payment-refund-billing",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "session-lifecycle",
            "data-export",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "payment-webhook-contract-parallel-controls"
    workflow_intents._replace_payment_webhook_ledger_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "webhook_contract_inspector", "role_definition_key": "webhook-contract-inspector"},
        {"id": "payment_webhook_builder", "role_definition_key": "payment-webhook-builder"},
        {"id": "webhook_evidence_inspector", "role_definition_key": "webhook-evidence-inspector"},
        {"id": "ledger_reconciliation_inspector", "role_definition_key": "ledger-reconciliation-inspector"},
        {"id": "payment_webhook_gatekeeper", "role_definition_key": "payment-webhook-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "webhook_contract_inspection_step", "role_id": "webhook_contract_inspector", "on_pass": "continue"},
        {
            "id": "payment_webhook_builder_step",
            "role_id": "payment_webhook_builder",
            "inputs": {
                "handoffs_from": ["webhook_contract_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": contract_verifies,
                    "limit": 36,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "webhook_evidence_inspection_step",
            "role_id": "webhook_evidence_inspector",
            "parallel_group": "payment_webhook_review_pack",
            "inputs": {
                "handoffs_from": ["webhook_contract_inspection_step", "payment_webhook_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": webhook_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "ledger_reconciliation_inspection_step",
            "role_id": "ledger_reconciliation_inspector",
            "parallel_group": "payment_webhook_review_pack",
            "inputs": {
                "handoffs_from": ["webhook_contract_inspection_step", "payment_webhook_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": ledger_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "payment_webhook_gatekeeper_step",
            "role_id": "payment_webhook_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "webhook_contract_inspection_step",
                    "payment_webhook_builder_step",
                    "webhook_evidence_inspection_step",
                    "ledger_reconciliation_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 60,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
