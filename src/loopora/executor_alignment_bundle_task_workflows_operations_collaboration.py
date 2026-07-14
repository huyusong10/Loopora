from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_concurrency_conflict_resolution_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify not in {"inventory-reservation", "quota-metering", "webhook-ordering"}]
    contract_verifies = _dedupe_values(
        [
            "conflict-resolution",
            "idempotency",
            "permission-auth",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    conflict_verifies = _dedupe_values(
        [
            "conflict-resolution",
            "idempotency",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    permission_audit_verifies = _dedupe_values(
        [
            "conflict-resolution",
            "permission-auth",
            "audit-log",
            "monitoring",
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
            "conflict-resolution",
            "idempotency",
            "permission-auth",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "collaborative-conflict-contract-parallel-resolution"
    workflow_intents._replace_concurrency_conflict_resolution_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "conflict_contract_inspector", "role_definition_key": "conflict-contract-inspector"},
        {"id": "collaboration_builder", "role_definition_key": "collaboration-builder"},
        {"id": "conflict_evidence_inspector", "role_definition_key": "conflict-evidence-inspector"},
        {"id": "permission_audit_inspector", "role_definition_key": "permission-audit-inspector"},
        {"id": "conflict_resolution_gatekeeper", "role_definition_key": "conflict-resolution-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "conflict_contract_inspection_step",
            "role_id": "conflict_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "collaboration_builder_step",
            "role_id": "collaboration_builder",
            "inputs": {"handoffs_from": ["conflict_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "conflict_evidence_inspection_step",
            "role_id": "conflict_evidence_inspector",
            "parallel_group": "conflict_resolution_review_pack",
            "inputs": {
                "handoffs_from": ["conflict_contract_inspection_step", "collaboration_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": conflict_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "permission_audit_inspection_step",
            "role_id": "permission_audit_inspector",
            "parallel_group": "conflict_resolution_review_pack",
            "inputs": {
                "handoffs_from": ["conflict_contract_inspection_step", "collaboration_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": permission_audit_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "conflict_resolution_gatekeeper_step",
            "role_id": "conflict_resolution_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "conflict_contract_inspection_step",
                    "collaboration_builder_step",
                    "conflict_evidence_inspection_step",
                    "permission_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
