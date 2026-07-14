from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_data_lifecycle_deletion_retention_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "deletion-retention",
            "tenant-isolation",
            "privacy-redaction",
            "audit-log",
            "permission-auth",
            "monitoring",
            "backup-restore",
            "cache-invalidation",
            "event-integrity",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    deletion_verifies = _dedupe_values(
        [
            "deletion-retention",
            "tenant-isolation",
            "privacy-redaction",
            "cache-invalidation",
            "event-integrity",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    retention_verifies = _dedupe_values(
        [
            "deletion-retention",
            "retention-policy",
            "backup-restore",
            "permission-auth",
            "audit-log",
            "monitoring",
            "privacy-redaction",
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
            "deletion-retention",
            "tenant-isolation",
            "privacy-redaction",
            "audit-log",
            "permission-auth",
            "monitoring",
            "backup-restore",
            "cache-invalidation",
            "event-integrity",
            "negative_evidence",
            "retention-policy",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "data-lifecycle-contract-parallel-deletion-retention"
    workflow_intents._replace_data_lifecycle_deletion_retention_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "data_lifecycle_contract_inspector", "role_definition_key": "data-lifecycle-contract-inspector"},
        {"id": "deletion_builder", "role_definition_key": "deletion-builder"},
        {"id": "privacy_deletion_evidence_inspector", "role_definition_key": "privacy-deletion-evidence-inspector"},
        {"id": "retention_audit_inspector", "role_definition_key": "retention-audit-inspector"},
        {"id": "data_lifecycle_gatekeeper", "role_definition_key": "data-lifecycle-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "data_lifecycle_contract_inspection_step",
            "role_id": "data_lifecycle_contract_inspector",
            "on_pass": "continue",
        },
        {
            "id": "deletion_builder_step",
            "role_id": "deletion_builder",
            "inputs": {
                "handoffs_from": ["data_lifecycle_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 36},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "privacy_deletion_evidence_inspection_step",
            "role_id": "privacy_deletion_evidence_inspector",
            "parallel_group": "data_lifecycle_review_pack",
            "inputs": {
                "handoffs_from": ["data_lifecycle_contract_inspection_step", "deletion_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": deletion_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "retention_audit_inspection_step",
            "role_id": "retention_audit_inspector",
            "parallel_group": "data_lifecycle_review_pack",
            "inputs": {
                "handoffs_from": ["data_lifecycle_contract_inspection_step", "deletion_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": retention_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "data_lifecycle_gatekeeper_step",
            "role_id": "data_lifecycle_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "data_lifecycle_contract_inspection_step",
                    "deletion_builder_step",
                    "privacy_deletion_evidence_inspection_step",
                    "retention_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
