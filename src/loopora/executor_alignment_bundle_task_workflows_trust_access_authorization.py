from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_authorization_policy_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "authorization-policy",
            "permission-auth",
            "identity-provisioning",
            "backward-compatibility",
            "cache-invalidation",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    security_verifies = _dedupe_values(
        [
            "authorization-policy",
            "tenant-isolation",
            "negative_evidence",
            "privacy-redaction",
            "data-export",
            "audit-log",
            "cache-invalidation",
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
            "authorization-policy",
            "tenant-isolation",
            "permission-auth",
            "cache-invalidation",
            "data-export",
            "audit-log",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "authorization-policy-parallel-inspection"
    workflow_intents._replace_authorization_policy_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "policy_builder", "role_definition_key": "authorization-policy-builder"},
        {"id": "contract_inspector", "role_definition_key": "authorization-contract-inspector"},
        {"id": "security_evidence_inspector", "role_definition_key": "authorization-security-inspector"},
        {"id": "authorization_gatekeeper", "role_definition_key": "authorization-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "policy_builder_step", "role_id": "policy_builder", "on_pass": "continue"},
        {
            "id": "contract_inspection_step",
            "role_id": "contract_inspector",
            "parallel_group": "authorization_review_pack",
            "inputs": {
                "handoffs_from": ["policy_builder_step"],
                "evidence_query": {
                    "archetypes": ["builder"],
                    "verifies": contract_verifies,
                    "limit": 28,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "security_evidence_inspection_step",
            "role_id": "security_evidence_inspector",
            "parallel_group": "authorization_review_pack",
            "inputs": {
                "handoffs_from": ["policy_builder_step"],
                "evidence_query": {
                    "archetypes": ["builder"],
                    "verifies": security_verifies,
                    "limit": 32,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "authorization_gatekeeper_step",
            "role_id": "authorization_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "policy_builder_step",
                    "contract_inspection_step",
                    "security_evidence_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["builder", "inspector"],
                    "verifies": gatekeeper_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]


__all__ = ("_replace_authorization_policy_task_workflow",)
