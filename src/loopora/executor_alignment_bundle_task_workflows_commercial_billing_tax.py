from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_tax_calculation_compliance_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify != "message-delivery"]
    contract_verifies = _dedupe_values(
        [
            "tax-compliance",
            "provider-contract",
            "idempotency",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    jurisdiction_verifies = _dedupe_values(
        [
            "tax-compliance",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection_verifies,
        ]
    )
    invoice_verifies = _dedupe_values(
        [
            "tax-compliance",
            "payment-refund-billing",
            "ledger-reconciliation",
            "provider-contract",
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
            "tax-compliance",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "ledger-reconciliation",
            "payment-refund-billing",
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
    workflow["preset"] = "tax-calculation-contract-parallel-compliance"
    workflow_intents._replace_tax_calculation_compliance_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "tax_contract_inspector", "role_definition_key": "tax-contract-inspector"},
        {"id": "tax_calculation_builder", "role_definition_key": "tax-calculation-builder"},
        {"id": "jurisdiction_rate_inspector", "role_definition_key": "jurisdiction-rate-inspector"},
        {"id": "invoice_reversal_inspector", "role_definition_key": "invoice-reversal-inspector"},
        {"id": "tax_compliance_gatekeeper", "role_definition_key": "tax-compliance-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "tax_contract_inspection_step", "role_id": "tax_contract_inspector", "on_pass": "continue"},
        {
            "id": "tax_calculation_builder_step",
            "role_id": "tax_calculation_builder",
            "inputs": {
                "handoffs_from": ["tax_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "jurisdiction_rate_inspection_step",
            "role_id": "jurisdiction_rate_inspector",
            "parallel_group": "tax_calculation_review_pack",
            "inputs": {
                "handoffs_from": ["tax_contract_inspection_step", "tax_calculation_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": jurisdiction_verifies,
                    "limit": 48,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "invoice_reversal_inspection_step",
            "role_id": "invoice_reversal_inspector",
            "parallel_group": "tax_calculation_review_pack",
            "inputs": {
                "handoffs_from": ["tax_contract_inspection_step", "tax_calculation_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": invoice_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "tax_compliance_gatekeeper_step",
            "role_id": "tax_compliance_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "tax_contract_inspection_step",
                    "tax_calculation_builder_step",
                    "jurisdiction_rate_inspection_step",
                    "invoice_reversal_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
