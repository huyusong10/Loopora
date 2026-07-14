from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_notification_subscription_deliverability_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify
        for verify in projection.evidence_verifies
        if verify not in {"quota-metering", "ledger-reconciliation", "payment-refund-billing", "payout-settlement"}
    ]
    contract_verifies = _dedupe_values(
        [
            "subscription-deliverability",
            "message-delivery",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "privacy-redaction",
            "locale-i18n",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    deliverability_verifies = _dedupe_values(
        [
            "subscription-deliverability",
            "message-delivery",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    template_privacy_verifies = _dedupe_values(
        [
            "subscription-deliverability",
            "privacy-redaction",
            "locale-i18n",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
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
            "subscription-deliverability",
            "message-delivery",
            "provider-contract",
            "idempotency",
            "retry-timeout",
            "queue-recovery",
            "privacy-redaction",
            "locale-i18n",
            "audit-log",
            "monitoring",
            "backward-compatibility",
            "migration-rollback",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "notification-subscription-contract-parallel-deliverability"
    workflow_intents._replace_notification_subscription_deliverability_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "notification_contract_inspector", "role_definition_key": "notification-contract-inspector"},
        {"id": "campaign_email_builder", "role_definition_key": "campaign-email-builder"},
        {"id": "deliverability_evidence_inspector", "role_definition_key": "deliverability-evidence-inspector"},
        {"id": "template_privacy_inspector", "role_definition_key": "template-privacy-inspector"},
        {"id": "notification_deliverability_gatekeeper", "role_definition_key": "notification-deliverability-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "notification_contract_inspection_step",
            "role_id": "notification_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 24}},
            "on_pass": "continue",
        },
        {
            "id": "campaign_email_builder_step",
            "role_id": "campaign_email_builder",
            "inputs": {"handoffs_from": ["notification_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "deliverability_evidence_inspection_step",
            "role_id": "deliverability_evidence_inspector",
            "parallel_group": "notification_deliverability_review_pack",
            "inputs": {
                "handoffs_from": ["notification_contract_inspection_step", "campaign_email_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": deliverability_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "template_privacy_inspection_step",
            "role_id": "template_privacy_inspector",
            "parallel_group": "notification_deliverability_review_pack",
            "inputs": {
                "handoffs_from": ["notification_contract_inspection_step", "campaign_email_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": template_privacy_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "notification_deliverability_gatekeeper_step",
            "role_id": "notification_deliverability_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "notification_contract_inspection_step",
                    "campaign_email_builder_step",
                    "deliverability_evidence_inspection_step",
                    "template_privacy_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
