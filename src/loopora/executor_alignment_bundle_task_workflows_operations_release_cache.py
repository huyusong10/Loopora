from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_cache_invalidation_consistency_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "cache-invalidation",
            "audit-log",
            "monitoring",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    stale_read_verifies = _dedupe_values(
        [
            "cache-invalidation",
            "negative_evidence",
            "migration-rollback",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    checkout_verifies = _dedupe_values(
        [
            "cache-invalidation",
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
            "cache-invalidation",
            "payment-refund-billing",
            "audit-log",
            "monitoring",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "cache-invalidation-contract-parallel-consistency"
    workflow_intents._replace_cache_invalidation_consistency_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "cache_contract_inspector", "role_definition_key": "cache-contract-inspector"},
        {"id": "price_cache_builder", "role_definition_key": "price-cache-builder"},
        {"id": "stale_read_evidence_inspector", "role_definition_key": "stale-read-evidence-inspector"},
        {"id": "checkout_price_integrity_inspector", "role_definition_key": "checkout-price-integrity-inspector"},
        {"id": "cache_consistency_gatekeeper", "role_definition_key": "cache-consistency-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "cache_contract_inspection_step", "role_id": "cache_contract_inspector", "on_pass": "continue"},
        {
            "id": "price_cache_builder_step",
            "role_id": "price_cache_builder",
            "inputs": {
                "handoffs_from": ["cache_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 36},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "stale_read_evidence_inspection_step",
            "role_id": "stale_read_evidence_inspector",
            "parallel_group": "cache_invalidation_review_pack",
            "inputs": {
                "handoffs_from": ["cache_contract_inspection_step", "price_cache_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": stale_read_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "checkout_price_integrity_inspection_step",
            "role_id": "checkout_price_integrity_inspector",
            "parallel_group": "cache_invalidation_review_pack",
            "inputs": {
                "handoffs_from": ["cache_contract_inspection_step", "price_cache_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": checkout_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "cache_consistency_gatekeeper_step",
            "role_id": "cache_consistency_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "cache_contract_inspection_step",
                    "price_cache_builder_step",
                    "stale_read_evidence_inspection_step",
                    "checkout_price_integrity_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
