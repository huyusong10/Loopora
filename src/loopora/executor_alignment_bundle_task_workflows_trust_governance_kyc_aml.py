from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import _replace_kyc_aml_screening_visible_scaffold
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_kyc_aml_screening_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "kyc-aml-screening",
            "provider-contract",
            "webhook-ordering",
            "deletion-retention",
            "privacy-redaction",
            "human-review",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    screening_verifies = _dedupe_values(
        [
            "kyc-aml-screening",
            "provider-contract",
            "webhook-ordering",
            "negative_evidence",
            "human-review",
            "retry-timeout",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    financial_verifies = _dedupe_values(
        [
            "kyc-aml-screening",
            "payout-settlement",
            "ledger-reconciliation",
            "privacy-redaction",
            "deletion-retention",
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
            "kyc-aml-screening",
            "provider-contract",
            "webhook-ordering",
            "payout-settlement",
            "ledger-reconciliation",
            "privacy-redaction",
            "human-review",
            "monitoring",
            "audit-log",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "kyc-aml-compliance-parallel-controls"
    _replace_kyc_aml_screening_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow_intents._replace_kyc_aml_screening_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "compliance_contract_inspector", "role_definition_key": "compliance-contract-inspector"},
        {"id": "kyc_aml_builder", "role_definition_key": "kyc-aml-builder"},
        {"id": "screening_evidence_inspector", "role_definition_key": "screening-evidence-inspector"},
        {"id": "financial_controls_inspector", "role_definition_key": "financial-controls-inspector"},
        {"id": "kyc_aml_gatekeeper", "role_definition_key": "kyc-aml-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "compliance_contract_inspection_step", "role_id": "compliance_contract_inspector", "on_pass": "continue"},
        {
            "id": "kyc_builder_step",
            "role_id": "kyc_aml_builder",
            "inputs": {
                "handoffs_from": ["compliance_contract_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": contract_verifies,
                    "limit": 32,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "screening_evidence_inspection_step",
            "role_id": "screening_evidence_inspector",
            "parallel_group": "kyc_aml_review_pack",
            "inputs": {
                "handoffs_from": ["compliance_contract_inspection_step", "kyc_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": screening_verifies,
                    "limit": 40,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "financial_controls_inspection_step",
            "role_id": "financial_controls_inspector",
            "parallel_group": "kyc_aml_review_pack",
            "inputs": {
                "handoffs_from": ["compliance_contract_inspection_step", "kyc_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": financial_verifies,
                    "limit": 40,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "kyc_aml_gatekeeper_step",
            "role_id": "kyc_aml_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "compliance_contract_inspection_step",
                    "kyc_builder_step",
                    "screening_evidence_inspection_step",
                    "financial_controls_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 56,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
