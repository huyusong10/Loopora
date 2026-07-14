from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_file_upload_storage_safety_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "file-upload-safety",
            "tenant-isolation",
            "permission-auth",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    access_verifies = _dedupe_values(
        [
            "file-upload-safety",
            "tenant-isolation",
            "permission-auth",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    malware_verifies = _dedupe_values(
        [
            "file-upload-safety",
            "privacy-redaction",
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
            "file-upload-safety",
            "tenant-isolation",
            "permission-auth",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "file-upload-contract-parallel-storage-safety"
    workflow_intents._replace_file_upload_storage_safety_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "upload_storage_contract_inspector", "role_definition_key": "upload-storage-contract-inspector"},
        {"id": "file_upload_builder", "role_definition_key": "file-upload-builder"},
        {"id": "storage_access_inspector", "role_definition_key": "storage-access-inspector"},
        {"id": "malware_cleanup_inspector", "role_definition_key": "malware-cleanup-inspector"},
        {"id": "upload_storage_gatekeeper", "role_definition_key": "upload-storage-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "upload_storage_contract_inspection_step", "role_id": "upload_storage_contract_inspector", "on_pass": "continue"},
        {
            "id": "file_upload_builder_step",
            "role_id": "file_upload_builder",
            "inputs": {
                "handoffs_from": ["upload_storage_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "storage_access_inspection_step",
            "role_id": "storage_access_inspector",
            "parallel_group": "file_upload_review_pack",
            "inputs": {
                "handoffs_from": ["upload_storage_contract_inspection_step", "file_upload_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": access_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "malware_cleanup_inspection_step",
            "role_id": "malware_cleanup_inspector",
            "parallel_group": "file_upload_review_pack",
            "inputs": {
                "handoffs_from": ["upload_storage_contract_inspection_step", "file_upload_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": malware_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "upload_storage_gatekeeper_step",
            "role_id": "upload_storage_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "upload_storage_contract_inspection_step",
                    "file_upload_builder_step",
                    "storage_access_inspection_step",
                    "malware_cleanup_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
