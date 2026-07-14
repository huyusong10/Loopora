from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import _replace_data_residency_visible_scaffold
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_data_residency_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "regional-isolation",
            "tenant-isolation",
            "provider-contract",
            "backup-restore",
            "search-index",
            "event-integrity",
            "privacy-redaction",
            "data-export",
            "monitoring",
            "audit-log",
            "migration-rollback",
            "permission-auth",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    evidence_verifies = _dedupe_values(
        [
            "regional-isolation",
            "tenant-isolation",
            "provider-contract",
            "backup-restore",
            "search-index",
            "event-integrity",
            "privacy-redaction",
            "data-export",
            "monitoring",
            "audit-log",
            "migration-rollback",
            "permission-auth",
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
            "regional-isolation",
            "tenant-isolation",
            "provider-contract",
            "backup-restore",
            "search-index",
            "event-integrity",
            "privacy-redaction",
            "data-export",
            "monitoring",
            "audit-log",
            "migration-rollback",
            "permission-auth",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "data-residency-contract-first"
    _replace_data_residency_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow_intents._replace_data_residency_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "residency_contract_inspector", "role_definition_key": "residency-contract-inspector"},
        {"id": "regional_isolation_builder", "role_definition_key": "regional-isolation-builder"},
        {"id": "residency_evidence_inspector", "role_definition_key": "residency-evidence-inspector"},
        {"id": "residency_gatekeeper", "role_definition_key": "residency-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "residency_contract_inspection_step",
            "role_id": "residency_contract_inspector",
            "on_pass": "continue",
        },
        {
            "id": "regional_isolation_builder_step",
            "role_id": "regional_isolation_builder",
            "inputs": {
                "handoffs_from": ["residency_contract_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": contract_verifies,
                    "limit": 32,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "residency_evidence_inspection_step",
            "role_id": "residency_evidence_inspector",
            "inputs": {
                "handoffs_from": ["residency_contract_inspection_step", "regional_isolation_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": evidence_verifies,
                    "limit": 48,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "residency_gatekeeper_step",
            "role_id": "residency_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "residency_contract_inspection_step",
                    "regional_isolation_builder_step",
                    "residency_evidence_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 56,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
