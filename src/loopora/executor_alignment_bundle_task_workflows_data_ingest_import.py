from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_data_import_validation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "data-import-validation",
            "idempotency",
            "permission-auth",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    import_verifies = _dedupe_values(
        [
            "data-import-validation",
            "idempotency",
            "negative_evidence",
            "monitoring",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    privacy_verifies = _dedupe_values(
        [
            "data-import-validation",
            "privacy-redaction",
            "permission-auth",
            "audit-log",
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
            "data-import-validation",
            "idempotency",
            "permission-auth",
            "privacy-redaction",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "data-import-contract-parallel-validation"
    workflow_intents._replace_data_import_validation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "import_contract_inspector", "role_definition_key": "import-contract-inspector"},
        {"id": "csv_import_builder", "role_definition_key": "csv-import-builder"},
        {"id": "import_evidence_inspector", "role_definition_key": "import-evidence-inspector"},
        {"id": "privacy_audit_inspector", "role_definition_key": "privacy-audit-inspector"},
        {"id": "import_validation_gatekeeper", "role_definition_key": "import-validation-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "import_contract_inspection_step", "role_id": "import_contract_inspector", "on_pass": "continue"},
        {
            "id": "csv_import_builder_step",
            "role_id": "csv_import_builder",
            "inputs": {
                "handoffs_from": ["import_contract_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "verifies": contract_verifies, "limit": 36},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "import_evidence_inspection_step",
            "role_id": "import_evidence_inspector",
            "parallel_group": "data_import_review_pack",
            "inputs": {
                "handoffs_from": ["import_contract_inspection_step", "csv_import_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": import_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "privacy_audit_inspection_step",
            "role_id": "privacy_audit_inspector",
            "parallel_group": "data_import_review_pack",
            "inputs": {
                "handoffs_from": ["import_contract_inspection_step", "csv_import_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": privacy_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "import_validation_gatekeeper_step",
            "role_id": "import_validation_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "import_contract_inspection_step",
                    "csv_import_builder_step",
                    "import_evidence_inspection_step",
                    "privacy_audit_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
