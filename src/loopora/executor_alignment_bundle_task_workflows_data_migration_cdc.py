from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_cdc_replication_consistency_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify not in {"webhook-ordering", "payment-ledger", "billing-ledger"}]
    contract_verifies = _dedupe_values(
        [
            "cdc-replication",
            "provider-contract",
            "event-ordering",
            "idempotency",
            "schema-evolution",
            "backfill-consistency",
            "delete-tombstone",
            "tenant-isolation",
            "warehouse-reconciliation",
            "monitoring",
            "connector-recovery",
            "audit-log",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    replication_verifies = _dedupe_values(
        [
            "cdc-replication",
            "provider-contract",
            "event-ordering",
            "idempotency",
            "schema-evolution",
            "delete-tombstone",
            "tenant-isolation",
            "negative_evidence",
            "audit-log",
            "local-governance",
            *projection_verifies,
        ]
    )
    reconciliation_verifies = _dedupe_values(
        [
            "cdc-replication",
            "provider-contract",
            "backfill-consistency",
            "warehouse-reconciliation",
            "monitoring",
            "connector-recovery",
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
            "cdc-replication",
            "provider-contract",
            "event-ordering",
            "idempotency",
            "schema-evolution",
            "backfill-consistency",
            "delete-tombstone",
            "tenant-isolation",
            "warehouse-reconciliation",
            "monitoring",
            "connector-recovery",
            "audit-log",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "cdc-replication-contract-parallel-consistency"
    workflow_intents._replace_cdc_replication_consistency_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "cdc_contract_inspector", "role_definition_key": "cdc-contract-inspector"},
        {"id": "cdc_pipeline_builder", "role_definition_key": "cdc-pipeline-builder"},
        {"id": "replication_evidence_inspector", "role_definition_key": "replication-evidence-inspector"},
        {"id": "reconciliation_lag_inspector", "role_definition_key": "reconciliation-lag-inspector"},
        {"id": "cdc_replication_gatekeeper", "role_definition_key": "cdc-replication-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "cdc_contract_inspection_step",
            "role_id": "cdc_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "cdc_pipeline_builder_step",
            "role_id": "cdc_pipeline_builder",
            "inputs": {"handoffs_from": ["cdc_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "replication_evidence_inspection_step",
            "role_id": "replication_evidence_inspector",
            "parallel_group": "cdc_replication_review_pack",
            "inputs": {
                "handoffs_from": ["cdc_contract_inspection_step", "cdc_pipeline_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": replication_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "reconciliation_lag_inspection_step",
            "role_id": "reconciliation_lag_inspector",
            "parallel_group": "cdc_replication_review_pack",
            "inputs": {
                "handoffs_from": ["cdc_contract_inspection_step", "cdc_pipeline_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": reconciliation_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "cdc_replication_gatekeeper_step",
            "role_id": "cdc_replication_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "cdc_contract_inspection_step",
                    "cdc_pipeline_builder_step",
                    "replication_evidence_inspection_step",
                    "reconciliation_lag_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
