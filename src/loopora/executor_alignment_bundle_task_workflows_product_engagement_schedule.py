from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_product import (
    _replace_schedule_phase_visible_scaffold,
)


def _replace_schedule_phase_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    workflow = bundle["workflow"]
    workflow["preset"] = "schedule-timezone-contract-parallel-recurrence"
    _replace_schedule_phase_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow_intents._replace_schedule_phase_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "schedule_contract_inspector", "role_definition_key": "schedule-contract-inspector"},
        {"id": "digest_scheduler_builder", "role_definition_key": "digest-scheduler-builder"},
        {"id": "temporal_correctness_inspector", "role_definition_key": "temporal-correctness-inspector"},
        {"id": "delivery_audit_inspector", "role_definition_key": "delivery-audit-inspector"},
        {"id": "schedule_gatekeeper", "role_definition_key": "schedule-gatekeeper"},
    ]
    contract_verifies = [
        "timezone-recurrence",
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "idempotency",
        "audit-log",
        "monitoring",
        "retry-timeout",
        "queue-recovery",
        "locale-i18n",
        "backward-compatibility",
        "migration-rollback",
        "task_anchor",
        "local-governance",
    ]
    temporal_verifies = [
        "timezone-recurrence",
        "idempotency",
        "retry-timeout",
        "queue-recovery",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ]
    delivery_verifies = [
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "audit-log",
        "locale-i18n",
        "monitoring",
        "backward-compatibility",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ]
    gatekeeper_verifies = [
        "done_when",
        "fake_done",
        "evidence_buckets",
        "residual_risk",
        "timezone-recurrence",
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "idempotency",
        "audit-log",
        "monitoring",
        "retry-timeout",
        "queue-recovery",
        "locale-i18n",
        "backward-compatibility",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ]
    workflow["steps"] = [
        {
            "id": "schedule_contract_inspection_step",
            "role_id": "schedule_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "digest_scheduler_builder_step",
            "role_id": "digest_scheduler_builder",
            "inputs": {"handoffs_from": ["schedule_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "temporal_correctness_inspection_step",
            "role_id": "temporal_correctness_inspector",
            "parallel_group": "schedule_timezone_review_pack",
            "inputs": {
                "handoffs_from": ["schedule_contract_inspection_step", "digest_scheduler_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": temporal_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "delivery_audit_inspection_step",
            "role_id": "delivery_audit_inspector",
            "parallel_group": "schedule_timezone_review_pack",
            "inputs": {
                "handoffs_from": ["schedule_contract_inspection_step", "digest_scheduler_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": delivery_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "schedule_gatekeeper_step",
            "role_id": "schedule_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "schedule_contract_inspection_step",
                    "digest_scheduler_builder_step",
                    "temporal_correctness_inspection_step",
                    "delivery_audit_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["builder", "inspector"],
                    "verifies": gatekeeper_verifies,
                    "limit": 56,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
