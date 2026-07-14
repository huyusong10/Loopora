from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_feature_flag_rollout_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "rollout-safety",
            "experiment-assignment",
            "monitoring",
            "audit-log",
            "payment-refund-billing",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    exposure_verifies = _dedupe_values(
        [
            "rollout-safety",
            "experiment-assignment",
            "negative_evidence",
            "audit-log",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    rollback_verifies = _dedupe_values(
        [
            "rollout-safety",
            "monitoring",
            "payment-refund-billing",
            "audit-log",
            "migration-rollback",
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
            "rollout-safety",
            "experiment-assignment",
            "monitoring",
            "audit-log",
            "payment-refund-billing",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "feature-flag-rollout-contract-parallel-release"
    workflow_intents._replace_feature_flag_rollout_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "rollout_contract_inspector", "role_definition_key": "rollout-contract-inspector"},
        {"id": "rollout_builder", "role_definition_key": "rollout-builder"},
        {"id": "exposure_consistency_inspector", "role_definition_key": "exposure-consistency-inspector"},
        {"id": "operational_rollback_inspector", "role_definition_key": "operational-rollback-inspector"},
        {"id": "release_rollout_gatekeeper", "role_definition_key": "release-rollout-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "rollout_contract_inspection_step", "role_id": "rollout_contract_inspector", "on_pass": "continue"},
        {
            "id": "rollout_builder_step",
            "role_id": "rollout_builder",
            "inputs": {
                "handoffs_from": ["rollout_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 36},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "exposure_consistency_inspection_step",
            "role_id": "exposure_consistency_inspector",
            "parallel_group": "feature_rollout_review_pack",
            "inputs": {
                "handoffs_from": ["rollout_contract_inspection_step", "rollout_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": exposure_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "operational_rollback_inspection_step",
            "role_id": "operational_rollback_inspector",
            "parallel_group": "feature_rollout_review_pack",
            "inputs": {
                "handoffs_from": ["rollout_contract_inspection_step", "rollout_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": rollback_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "release_rollout_gatekeeper_step",
            "role_id": "release_rollout_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "rollout_contract_inspection_step",
                    "rollout_builder_step",
                    "exposure_consistency_inspection_step",
                    "operational_rollback_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
