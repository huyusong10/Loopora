from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import _replace_key_rotation_visible_scaffold
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_key_rotation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "key-rotation",
            "privacy-redaction",
            "permission-auth",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "eval-set",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    lifecycle_verifies = _dedupe_values(
        [
            "key-rotation",
            "permission-auth",
            "negative_evidence",
            "monitoring",
            "backward-compatibility",
            "eval-set",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    storage_verifies = _dedupe_values(
        [
            "privacy-redaction",
            "audit-log",
            "key-rotation",
            "permission-auth",
            "monitoring",
            "eval-set",
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
            "key-rotation",
            "privacy-redaction",
            "permission-auth",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "eval-set",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "key-rotation-contract-parallel-controls"
    _replace_key_rotation_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow_intents._replace_key_rotation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "key_rotation_contract_inspector", "role_definition_key": "key-rotation-contract-inspector"},
        {"id": "secret_rotation_builder", "role_definition_key": "secret-rotation-builder"},
        {"id": "rotation_lifecycle_evidence_inspector", "role_definition_key": "rotation-lifecycle-evidence-inspector"},
        {"id": "secret_storage_audit_inspector", "role_definition_key": "secret-storage-audit-inspector"},
        {"id": "key_rotation_gatekeeper", "role_definition_key": "key-rotation-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "key_rotation_contract_inspection_step", "role_id": "key_rotation_contract_inspector", "on_pass": "continue"},
        {
            "id": "secret_rotation_builder_step",
            "role_id": "secret_rotation_builder",
            "inputs": {
                "handoffs_from": ["key_rotation_contract_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": contract_verifies,
                    "limit": 36,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "rotation_lifecycle_evidence_inspection_step",
            "role_id": "rotation_lifecycle_evidence_inspector",
            "parallel_group": "key_rotation_review_pack",
            "inputs": {
                "handoffs_from": ["key_rotation_contract_inspection_step", "secret_rotation_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": lifecycle_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "secret_storage_audit_inspection_step",
            "role_id": "secret_storage_audit_inspector",
            "parallel_group": "key_rotation_review_pack",
            "inputs": {
                "handoffs_from": ["key_rotation_contract_inspection_step", "secret_rotation_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": storage_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "key_rotation_gatekeeper_step",
            "role_id": "key_rotation_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "key_rotation_contract_inspection_step",
                    "secret_rotation_builder_step",
                    "rotation_lifecycle_evidence_inspection_step",
                    "secret_storage_audit_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 60,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
