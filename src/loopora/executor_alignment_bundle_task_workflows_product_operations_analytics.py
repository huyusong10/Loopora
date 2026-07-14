from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_analytics_experiment_instrumentation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify for verify in projection.evidence_verifies if verify not in {"subscription-deliverability", "message-delivery", "queue-recovery"}
    ]
    contract_verifies = _dedupe_values(
        [
            "event-integrity",
            "experiment-assignment",
            "idempotency",
            "identity-merge",
            "privacy-redaction",
            "warehouse-reconciliation",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    event_verifies = _dedupe_values(
        [
            "event-integrity",
            "idempotency",
            "identity-merge",
            "privacy-redaction",
            "warehouse-reconciliation",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    experiment_verifies = _dedupe_values(
        [
            "experiment-assignment",
            "event-integrity",
            "warehouse-reconciliation",
            "monitoring",
            "backward-compatibility",
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
            "event-integrity",
            "experiment-assignment",
            "idempotency",
            "identity-merge",
            "privacy-redaction",
            "warehouse-reconciliation",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "analytics-experiment-contract-parallel-instrumentation"
    workflow_intents._replace_analytics_experiment_instrumentation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "instrumentation_contract_inspector", "role_definition_key": "instrumentation-contract-inspector"},
        {"id": "tracking_builder", "role_definition_key": "tracking-builder"},
        {"id": "event_integrity_inspector", "role_definition_key": "event-integrity-inspector"},
        {"id": "experiment_consistency_inspector", "role_definition_key": "experiment-consistency-inspector"},
        {"id": "analytics_experiment_gatekeeper", "role_definition_key": "analytics-experiment-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "instrumentation_contract_inspection_step",
            "role_id": "instrumentation_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "tracking_builder_step",
            "role_id": "tracking_builder",
            "inputs": {"handoffs_from": ["instrumentation_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "event_integrity_inspection_step",
            "role_id": "event_integrity_inspector",
            "parallel_group": "analytics_experiment_review_pack",
            "inputs": {
                "handoffs_from": ["instrumentation_contract_inspection_step", "tracking_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": event_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "experiment_consistency_inspection_step",
            "role_id": "experiment_consistency_inspector",
            "parallel_group": "analytics_experiment_review_pack",
            "inputs": {
                "handoffs_from": ["instrumentation_contract_inspection_step", "tracking_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": experiment_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "analytics_experiment_gatekeeper_step",
            "role_id": "analytics_experiment_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "instrumentation_contract_inspection_step",
                    "tracking_builder_step",
                    "event_integrity_inspection_step",
                    "experiment_consistency_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
