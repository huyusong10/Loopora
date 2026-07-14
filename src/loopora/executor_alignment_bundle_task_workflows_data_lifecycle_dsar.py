from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_dsar_data_export_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "data-export",
            "privacy-redaction",
            "permission-auth",
            "tenant-isolation",
            "deletion-retention",
            "async-job-lifecycle",
            "idempotency",
            "audit-log",
            "message-delivery",
            "rate-limit",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    scope_verifies = _dedupe_values(
        [
            "data-export",
            "tenant-isolation",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    access_retention_verifies = _dedupe_values(
        [
            "data-export",
            "privacy-redaction",
            "permission-auth",
            "tenant-isolation",
            "deletion-retention",
            "async-job-lifecycle",
            "idempotency",
            "audit-log",
            "message-delivery",
            "rate-limit",
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
            "data-export",
            "privacy-redaction",
            "permission-auth",
            "tenant-isolation",
            "deletion-retention",
            "async-job-lifecycle",
            "idempotency",
            "audit-log",
            "message-delivery",
            "rate-limit",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "dsar-export-contract-parallel-privacy"
    workflow_intents._replace_dsar_data_export_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "dsar_export_contract_inspector", "role_definition_key": "dsar-export-contract-inspector"},
        {"id": "privacy_export_builder", "role_definition_key": "privacy-export-builder"},
        {"id": "export_scope_inspector", "role_definition_key": "export-scope-inspector"},
        {"id": "access_retention_audit_inspector", "role_definition_key": "access-retention-audit-inspector"},
        {"id": "dsar_export_gatekeeper", "role_definition_key": "dsar-export-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "dsar_export_contract_inspection_step", "role_id": "dsar_export_contract_inspector", "on_pass": "continue"},
        {
            "id": "privacy_export_builder_step",
            "role_id": "privacy_export_builder",
            "inputs": {
                "handoffs_from": ["dsar_export_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "export_scope_inspection_step",
            "role_id": "export_scope_inspector",
            "parallel_group": "dsar_export_review_pack",
            "inputs": {
                "handoffs_from": ["dsar_export_contract_inspection_step", "privacy_export_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": scope_verifies, "limit": 56},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "access_retention_audit_inspection_step",
            "role_id": "access_retention_audit_inspector",
            "parallel_group": "dsar_export_review_pack",
            "inputs": {
                "handoffs_from": ["dsar_export_contract_inspection_step", "privacy_export_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": access_retention_verifies,
                    "limit": 56,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "dsar_export_gatekeeper_step",
            "role_id": "dsar_export_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "dsar_export_contract_inspection_step",
                    "privacy_export_builder_step",
                    "export_scope_inspection_step",
                    "access_retention_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 76},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
