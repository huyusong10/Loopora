from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_visible_scaffolds_commercial import (
    _replace_metric_reporting_reconciliation_visible_scaffold,
)
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_metric_reporting_reconciliation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [verify for verify in projection.evidence_verifies if verify not in {"message-delivery", "experiment-assignment", "cdc-replication"}]
    contract_verifies = _dedupe_values(
        [
            "metric-reconciliation",
            "ledger-reconciliation",
            "provider-contract",
            "metric-definition",
            "edge-case-aggregation",
            "fx-cutoff-timezone",
            "locked-backfill",
            "permission-auth",
            "data-export",
            "audit-log",
            "monitoring",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    reconciliation_verifies = _dedupe_values(
        [
            "metric-reconciliation",
            "ledger-reconciliation",
            "provider-contract",
            "payment-refund-billing",
            "metric-definition",
            "edge-case-aggregation",
            "fx-cutoff-timezone",
            "data-export",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    permission_backfill_verifies = _dedupe_values(
        [
            "metric-reconciliation",
            "locked-backfill",
            "permission-auth",
            "tenant-isolation",
            "audit-log",
            "data-export",
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
            "metric-reconciliation",
            "ledger-reconciliation",
            "provider-contract",
            "payment-refund-billing",
            "metric-definition",
            "edge-case-aggregation",
            "fx-cutoff-timezone",
            "locked-backfill",
            "permission-auth",
            "tenant-isolation",
            "data-export",
            "audit-log",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "metric-reporting-contract-parallel-reconciliation"
    workflow_intents._replace_metric_reporting_reconciliation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "metric_contract_inspector", "role_definition_key": "metric-contract-inspector"},
        {"id": "revenue_dashboard_builder", "role_definition_key": "revenue-dashboard-builder"},
        {"id": "metric_reconciliation_inspector", "role_definition_key": "metric-reconciliation-inspector"},
        {"id": "permission_backfill_inspector", "role_definition_key": "permission-backfill-inspector"},
        {"id": "metric_reporting_gatekeeper", "role_definition_key": "metric-reporting-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "metric_contract_inspection_step",
            "role_id": "metric_contract_inspector",
            "inputs": {"evidence_query": {"archetypes": ["builder"], "verifies": contract_verifies, "limit": 28}},
            "on_pass": "continue",
        },
        {
            "id": "revenue_dashboard_builder_step",
            "role_id": "revenue_dashboard_builder",
            "inputs": {"handoffs_from": ["metric_contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "metric_reconciliation_inspection_step",
            "role_id": "metric_reconciliation_inspector",
            "parallel_group": "metric_reporting_review_pack",
            "inputs": {
                "handoffs_from": ["metric_contract_inspection_step", "revenue_dashboard_builder_step"],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": reconciliation_verifies, "limit": 44},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "permission_backfill_inspection_step",
            "role_id": "permission_backfill_inspector",
            "parallel_group": "metric_reporting_review_pack",
            "inputs": {
                "handoffs_from": ["metric_contract_inspection_step", "revenue_dashboard_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": permission_backfill_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "metric_reporting_gatekeeper_step",
            "role_id": "metric_reporting_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "metric_contract_inspection_step",
                    "revenue_dashboard_builder_step",
                    "metric_reconciliation_inspection_step",
                    "permission_backfill_inspection_step",
                ],
                "evidence_query": {"archetypes": ["inspector", "builder"], "verifies": gatekeeper_verifies, "limit": 60},
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
    _replace_metric_reporting_reconciliation_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        task=task,
        projection=projection,
    )
