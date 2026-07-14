from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_auth_session_token_lifecycle_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "session-lifecycle",
            "permission-auth",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    misuse_verifies = _dedupe_values(
        [
            "session-lifecycle",
            "permission-auth",
            "privacy-redaction",
            "tenant-isolation",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    revocation_verifies = _dedupe_values(
        [
            "session-lifecycle",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
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
            "session-lifecycle",
            "permission-auth",
            "privacy-redaction",
            "tenant-isolation",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "auth-session-token-contract-parallel-lifecycle"
    workflow_intents._replace_auth_session_token_lifecycle_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "session_token_contract_inspector", "role_definition_key": "session-token-contract-inspector"},
        {"id": "session_token_builder", "role_definition_key": "session-token-builder"},
        {"id": "token_misuse_inspector", "role_definition_key": "token-misuse-inspector"},
        {"id": "session_revocation_audit_inspector", "role_definition_key": "session-revocation-audit-inspector"},
        {"id": "auth_session_gatekeeper", "role_definition_key": "auth-session-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "session_token_contract_inspection_step", "role_id": "session_token_contract_inspector", "on_pass": "continue"},
        {
            "id": "session_token_builder_step",
            "role_id": "session_token_builder",
            "inputs": {
                "handoffs_from": ["session_token_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "token_misuse_inspection_step",
            "role_id": "token_misuse_inspector",
            "parallel_group": "auth_session_review_pack",
            "inputs": {
                "handoffs_from": ["session_token_contract_inspection_step", "session_token_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": misuse_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "session_revocation_audit_inspection_step",
            "role_id": "session_revocation_audit_inspector",
            "parallel_group": "auth_session_review_pack",
            "inputs": {
                "handoffs_from": ["session_token_contract_inspection_step", "session_token_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": revocation_verifies, "limit": 48},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "auth_session_gatekeeper_step",
            "role_id": "auth_session_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "session_token_contract_inspection_step",
                    "session_token_builder_step",
                    "token_misuse_inspection_step",
                    "session_revocation_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 64},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
