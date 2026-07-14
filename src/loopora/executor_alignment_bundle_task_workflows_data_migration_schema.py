from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_database_schema_migration_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify for verify in projection.evidence_verifies if verify not in {"subscription-deliverability", "message-delivery", "experiment-assignment"}
    ]
    contract_verifies = _dedupe_values(
        [
            "schema-migration",
            "provider-contract",
            "dual-write",
            "reader-compatibility",
            "tenant-isolation",
            "backfill-idempotency",
            "invoice-reconciliation",
            "monitoring",
            "rollback-recovery",
            "backward-compatibility",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    consistency_verifies = _dedupe_values(
        [
            "schema-migration",
            "provider-contract",
            "dual-write",
            "reader-compatibility",
            "tenant-isolation",
            "backfill-idempotency",
            "invoice-reconciliation",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    rollback_verifies = _dedupe_values(
        [
            "rollback-recovery",
            "provider-contract",
            "migration-rollback",
            "monitoring",
            "backfill-idempotency",
            "backward-compatibility",
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
            "schema-migration",
            "provider-contract",
            "dual-write",
            "reader-compatibility",
            "tenant-isolation",
            "backfill-idempotency",
            "invoice-reconciliation",
            "monitoring",
            "rollback-recovery",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "database-schema-migration-contract-parallel-backfill"
    workflow_intents._replace_database_schema_migration_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "migration_contract_inspector", "role_definition_key": "migration-contract-inspector"},
        {"id": "schema_migration_builder", "role_definition_key": "schema-migration-builder"},
        {"id": "data_consistency_inspector", "role_definition_key": "data-consistency-inspector"},
        {"id": "operational_rollback_inspector", "role_definition_key": "operational-rollback-inspector"},
        {"id": "migration_gatekeeper", "role_definition_key": "migration-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "migration_contract_inspection_step",
            "role_id": "migration_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "schema_migration_builder_step",
            "role_id": "schema_migration_builder",
            "inputs": {"handoffs_from": ["migration_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "data_consistency_inspection_step",
            "role_id": "data_consistency_inspector",
            "parallel_group": "database_migration_review_pack",
            "inputs": {
                "handoffs_from": ["migration_contract_inspection_step", "schema_migration_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": consistency_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "operational_rollback_inspection_step",
            "role_id": "operational_rollback_inspector",
            "parallel_group": "database_migration_review_pack",
            "inputs": {
                "handoffs_from": ["migration_contract_inspection_step", "schema_migration_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": rollback_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "migration_gatekeeper_step",
            "role_id": "migration_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "migration_contract_inspection_step",
                    "schema_migration_builder_step",
                    "data_consistency_inspection_step",
                    "operational_rollback_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
