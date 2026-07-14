from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_support_ticket_sla_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "support-ticket-lifecycle",
            "sla-escalation",
            "idempotency",
            "queue-recovery",
            "permission-auth",
            "tenant-isolation",
            "message-delivery",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    lifecycle_verifies = _dedupe_values(
        [
            "support-ticket-lifecycle",
            "sla-escalation",
            "idempotency",
            "queue-recovery",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    access_notification_verifies = _dedupe_values(
        [
            "support-ticket-lifecycle",
            "permission-auth",
            "tenant-isolation",
            "message-delivery",
            "audit-log",
            "privacy-redaction",
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
            "support-ticket-lifecycle",
            "sla-escalation",
            "idempotency",
            "queue-recovery",
            "permission-auth",
            "tenant-isolation",
            "message-delivery",
            "audit-log",
            "privacy-redaction",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "support-ticket-contract-parallel-sla"
    workflow_intents._replace_support_ticket_sla_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "support_ticket_contract_inspector", "role_definition_key": "support-ticket-contract-inspector"},
        {"id": "ticket_sla_builder", "role_definition_key": "ticket-sla-builder"},
        {"id": "ticket_lifecycle_inspector", "role_definition_key": "ticket-lifecycle-inspector"},
        {"id": "access_notification_audit_inspector", "role_definition_key": "access-notification-audit-inspector"},
        {"id": "support_ticket_gatekeeper", "role_definition_key": "support-ticket-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "support_ticket_contract_inspection_step", "role_id": "support_ticket_contract_inspector", "on_pass": "continue"},
        {
            "id": "ticket_sla_builder_step",
            "role_id": "ticket_sla_builder",
            "inputs": {
                "handoffs_from": ["support_ticket_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "ticket_lifecycle_inspection_step",
            "role_id": "ticket_lifecycle_inspector",
            "parallel_group": "support_ticket_review_pack",
            "inputs": {
                "handoffs_from": ["support_ticket_contract_inspection_step", "ticket_sla_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": lifecycle_verifies, "limit": 52},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "access_notification_audit_inspection_step",
            "role_id": "access_notification_audit_inspector",
            "parallel_group": "support_ticket_review_pack",
            "inputs": {
                "handoffs_from": ["support_ticket_contract_inspection_step", "ticket_sla_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": access_notification_verifies,
                    "limit": 52,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "support_ticket_gatekeeper_step",
            "role_id": "support_ticket_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "support_ticket_contract_inspection_step",
                    "ticket_sla_builder_step",
                    "ticket_lifecycle_inspection_step",
                    "access_notification_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 72},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
