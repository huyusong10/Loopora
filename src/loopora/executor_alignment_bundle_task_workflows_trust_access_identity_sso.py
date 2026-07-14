from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_identity_sso_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "sso-assertion",
            "identity-provisioning",
            "tenant-isolation",
            "permission-auth",
            "session-lifecycle",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    assertion_verifies = _dedupe_values(
        [
            "sso-assertion",
            "tenant-isolation",
            "session-lifecycle",
            "negative_evidence",
            "audit-log",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    provisioning_verifies = _dedupe_values(
        [
            "identity-provisioning",
            "permission-auth",
            "tenant-isolation",
            "backward-compatibility",
            "migration-rollback",
            "audit-log",
            "monitoring",
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
            "sso-assertion",
            "identity-provisioning",
            "tenant-isolation",
            "permission-auth",
            "session-lifecycle",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "identity-sso-contract-parallel-controls"
    workflow_intents._replace_identity_sso_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "identity_contract_inspector", "role_definition_key": "identity-contract-inspector"},
        {"id": "sso_builder", "role_definition_key": "sso-builder"},
        {"id": "sso_assertion_evidence_inspector", "role_definition_key": "sso-assertion-evidence-inspector"},
        {"id": "provisioning_mapping_inspector", "role_definition_key": "provisioning-mapping-inspector"},
        {"id": "identity_sso_gatekeeper", "role_definition_key": "identity-sso-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "identity_contract_inspection_step", "role_id": "identity_contract_inspector", "on_pass": "continue"},
        {
            "id": "sso_builder_step",
            "role_id": "sso_builder",
            "inputs": {
                "handoffs_from": ["identity_contract_inspection_step"],
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
            "id": "sso_assertion_evidence_inspection_step",
            "role_id": "sso_assertion_evidence_inspector",
            "parallel_group": "identity_sso_review_pack",
            "inputs": {
                "handoffs_from": ["identity_contract_inspection_step", "sso_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": assertion_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "provisioning_mapping_inspection_step",
            "role_id": "provisioning_mapping_inspector",
            "parallel_group": "identity_sso_review_pack",
            "inputs": {
                "handoffs_from": ["identity_contract_inspection_step", "sso_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": provisioning_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "identity_sso_gatekeeper_step",
            "role_id": "identity_sso_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "identity_contract_inspection_step",
                    "sso_builder_step",
                    "sso_assertion_evidence_inspection_step",
                    "provisioning_mapping_inspection_step",
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
