from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_inventory_reservation_consistency_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "inventory-reservation",
            "webhook-ordering",
            "idempotency",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    race_verifies = _dedupe_values(
        [
            "inventory-reservation",
            "conflict-resolution",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    payment_verifies = _dedupe_values(
        [
            "inventory-reservation",
            "webhook-ordering",
            "idempotency",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
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
            "inventory-reservation",
            "conflict-resolution",
            "webhook-ordering",
            "idempotency",
            "ledger-reconciliation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "inventory-reservation-contract-parallel-consistency"
    workflow_intents._replace_inventory_reservation_consistency_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "inventory_contract_inspector", "role_definition_key": "inventory-contract-inspector"},
        {"id": "inventory_reservation_builder", "role_definition_key": "inventory-reservation-builder"},
        {"id": "reservation_race_inspector", "role_definition_key": "reservation-race-inspector"},
        {"id": "payment_ledger_inspector", "role_definition_key": "payment-ledger-inspector"},
        {"id": "inventory_reservation_gatekeeper", "role_definition_key": "inventory-reservation-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "inventory_contract_inspection_step", "role_id": "inventory_contract_inspector", "on_pass": "continue"},
        {
            "id": "inventory_reservation_builder_step",
            "role_id": "inventory_reservation_builder",
            "inputs": {
                "handoffs_from": ["inventory_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "reservation_race_inspection_step",
            "role_id": "reservation_race_inspector",
            "parallel_group": "inventory_reservation_review_pack",
            "inputs": {
                "handoffs_from": ["inventory_contract_inspection_step", "inventory_reservation_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": race_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "payment_ledger_inspection_step",
            "role_id": "payment_ledger_inspector",
            "parallel_group": "inventory_reservation_review_pack",
            "inputs": {
                "handoffs_from": ["inventory_contract_inspection_step", "inventory_reservation_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": payment_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "inventory_reservation_gatekeeper_step",
            "role_id": "inventory_reservation_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "inventory_contract_inspection_step",
                    "inventory_reservation_builder_step",
                    "reservation_race_inspection_step",
                    "payment_ledger_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
