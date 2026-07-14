from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_search_index_consistency_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify not in {"eval-set", "human-review", "rag-grounding", "tool-safety"}]
    contract_verifies = _dedupe_values(
        [
            "search-index",
            "provider-contract",
            "permission-auth",
            "tenant-isolation",
            "idempotency",
            "monitoring",
            "audit-log",
            "retry-timeout",
            "queue-recovery",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    consistency_verifies = _dedupe_values(
        [
            "search-index",
            "provider-contract",
            "idempotency",
            "monitoring",
            "audit-log",
            "retry-timeout",
            "queue-recovery",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    access_verifies = _dedupe_values(
        [
            "search-index",
            "provider-contract",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "retry-timeout",
            "queue-recovery",
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
            "search-index",
            "provider-contract",
            "permission-auth",
            "tenant-isolation",
            "idempotency",
            "monitoring",
            "audit-log",
            "retry-timeout",
            "queue-recovery",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "search-index-contract-parallel-consistency"
    workflow_intents._replace_search_index_consistency_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "search_index_contract_inspector", "role_definition_key": "search-index-contract-inspector"},
        {"id": "search_index_builder", "role_definition_key": "search-index-builder"},
        {"id": "index_consistency_inspector", "role_definition_key": "index-consistency-inspector"},
        {"id": "access_freshness_inspector", "role_definition_key": "access-freshness-inspector"},
        {"id": "search_index_gatekeeper", "role_definition_key": "search-index-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "search_index_contract_inspection_step",
            "role_id": "search_index_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "search_index_builder_step",
            "role_id": "search_index_builder",
            "inputs": {
                "handoffs_from": ["search_index_contract_inspection_step"],
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "index_consistency_inspection_step",
            "role_id": "index_consistency_inspector",
            "parallel_group": "search_index_review_pack",
            "inputs": {
                "handoffs_from": ["search_index_contract_inspection_step", "search_index_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": consistency_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "access_freshness_inspection_step",
            "role_id": "access_freshness_inspector",
            "parallel_group": "search_index_review_pack",
            "inputs": {
                "handoffs_from": ["search_index_contract_inspection_step", "search_index_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": access_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "search_index_gatekeeper_step",
            "role_id": "search_index_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "search_index_contract_inspection_step",
                    "search_index_builder_step",
                    "index_consistency_inspection_step",
                    "access_freshness_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
