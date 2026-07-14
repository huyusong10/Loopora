from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_audit_log_integrity_retention_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify
        for verify in projection.evidence_verifies
        if verify not in {"dispute-chargeback", "message-delivery", "deletion-retention", "backup-restore", "cache-invalidation"}
    ]
    contract_verifies = _dedupe_values(
        [
            "audit-integrity",
            "audit-log",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "idempotency",
            "monitoring",
            "data-export",
            "retention-policy",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    integrity_verifies = _dedupe_values(
        [
            "audit-integrity",
            "audit-log",
            "privacy-redaction",
            "tenant-isolation",
            "idempotency",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection_verifies,
        ]
    )
    retention_export_verifies = _dedupe_values(
        [
            "audit-integrity",
            "audit-log",
            "permission-auth",
            "tenant-isolation",
            "data-export",
            "retention-policy",
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
            "audit-integrity",
            "audit-log",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "idempotency",
            "monitoring",
            "data-export",
            "retention-policy",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "audit-log-integrity-contract-parallel-retention"
    workflow_intents._replace_audit_log_integrity_retention_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "audit_contract_inspector", "role_definition_key": "audit-contract-inspector"},
        {"id": "audit_trail_builder", "role_definition_key": "audit-trail-builder"},
        {"id": "audit_integrity_inspector", "role_definition_key": "audit-integrity-inspector"},
        {"id": "retention_export_inspector", "role_definition_key": "retention-export-inspector"},
        {"id": "audit_compliance_gatekeeper", "role_definition_key": "audit-compliance-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "audit_contract_inspection_step", "role_id": "audit_contract_inspector", "on_pass": "continue"},
        {
            "id": "audit_trail_builder_step",
            "role_id": "audit_trail_builder",
            "inputs": {
                "handoffs_from": ["audit_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "audit_integrity_inspection_step",
            "role_id": "audit_integrity_inspector",
            "parallel_group": "audit_log_review_pack",
            "inputs": {
                "handoffs_from": ["audit_contract_inspection_step", "audit_trail_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": integrity_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "retention_export_inspection_step",
            "role_id": "retention_export_inspector",
            "parallel_group": "audit_log_review_pack",
            "inputs": {
                "handoffs_from": ["audit_contract_inspection_step", "audit_trail_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": retention_export_verifies,
                    "limit": 48,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "audit_compliance_gatekeeper_step",
            "role_id": "audit_compliance_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "audit_contract_inspection_step",
                    "audit_trail_builder_step",
                    "audit_integrity_inspection_step",
                    "retention_export_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
