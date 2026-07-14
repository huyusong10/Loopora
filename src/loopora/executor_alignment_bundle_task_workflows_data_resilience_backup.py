from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_backup_restore_recovery_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "backup-restore",
            "privacy-redaction",
            "migration-rollback",
            "monitoring",
            "audit-log",
            "permission-auth",
            "data-integrity",
            "retention-policy",
            "security-key-access",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    restore_verifies = _dedupe_values(
        [
            "backup-restore",
            "privacy-redaction",
            "migration-rollback",
            "data-integrity",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    retention_verifies = _dedupe_values(
        [
            "retention-policy",
            "security-key-access",
            "privacy-redaction",
            "permission-auth",
            "audit-log",
            "monitoring",
            "backup-restore",
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
            "backup-restore",
            "privacy-redaction",
            "migration-rollback",
            "monitoring",
            "audit-log",
            "permission-auth",
            "data-integrity",
            "retention-policy",
            "security-key-access",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "backup-restore-contract-parallel-recovery"
    workflow_intents._replace_backup_restore_recovery_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "backup_recovery_contract_inspector", "role_definition_key": "backup-recovery-contract-inspector"},
        {"id": "backup_restore_builder", "role_definition_key": "backup-restore-builder"},
        {"id": "restore_drill_evidence_inspector", "role_definition_key": "restore-drill-evidence-inspector"},
        {"id": "retention_security_audit_inspector", "role_definition_key": "retention-security-audit-inspector"},
        {"id": "backup_recovery_gatekeeper", "role_definition_key": "backup-recovery-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "backup_recovery_contract_inspection_step", "role_id": "backup_recovery_contract_inspector", "on_pass": "continue"},
        {
            "id": "backup_restore_builder_step",
            "role_id": "backup_restore_builder",
            "inputs": {
                "handoffs_from": ["backup_recovery_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 36},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "restore_drill_evidence_inspection_step",
            "role_id": "restore_drill_evidence_inspector",
            "parallel_group": "backup_restore_review_pack",
            "inputs": {
                "handoffs_from": ["backup_recovery_contract_inspection_step", "backup_restore_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": restore_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "retention_security_audit_inspection_step",
            "role_id": "retention_security_audit_inspector",
            "parallel_group": "backup_restore_review_pack",
            "inputs": {
                "handoffs_from": ["backup_recovery_contract_inspection_step", "backup_restore_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": retention_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "backup_recovery_gatekeeper_step",
            "role_id": "backup_recovery_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "backup_recovery_contract_inspection_step",
                    "backup_restore_builder_step",
                    "restore_drill_evidence_inspection_step",
                    "retention_security_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
