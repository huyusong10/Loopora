from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from loopora.executor_alignment_bundle_task_predicates import (
    _is_analytics_experiment_instrumentation_task,
    _is_audit_log_integrity_retention_task,
    _is_auth_session_token_lifecycle_task,
    _is_authorization_policy_task,
    _is_backup_restore_recovery_task,
    _is_cache_invalidation_consistency_task,
    _is_cdc_replication_consistency_task,
    _is_concurrency_conflict_resolution_task,
    _is_data_import_validation_task,
    _is_data_lifecycle_deletion_retention_task,
    _is_data_residency_task,
    _is_database_schema_migration_task,
    _is_dispute_chargeback_lifecycle_task,
    _is_dsar_data_export_task,
    _is_feature_flag_rollout_task,
    _is_file_upload_storage_safety_task,
    _is_identity_sso_task,
    _is_incident_root_cause_task,
    _is_inventory_reservation_consistency_task,
    _is_key_rotation_task,
    _is_kyc_aml_screening_task,
    _is_metric_reporting_reconciliation_task,
    _is_notification_subscription_deliverability_task,
    _is_payment_webhook_ledger_task,
    _is_payout_settlement_reconciliation_task,
    _is_prompt_asset_ownership_task,
    _is_rag_long_chain_task,
    _is_schedule_phase_task,
    _is_search_index_consistency_task,
    _is_search_quality_task,
    _is_subscription_entitlement_billing_task,
    _is_support_impersonation_task,
    _is_support_ticket_sla_task,
    _is_tax_calculation_compliance_task,
    _is_usage_quota_metering_task,
)
from loopora.executor_alignment_bundle_task_workflows_commercial import (
    _replace_dispute_chargeback_lifecycle_task_workflow,
    _replace_metric_reporting_reconciliation_task_workflow,
    _replace_payment_webhook_ledger_task_workflow,
    _replace_payout_settlement_reconciliation_task_workflow,
    _replace_subscription_entitlement_billing_task_workflow,
    _replace_tax_calculation_compliance_task_workflow,
    _replace_usage_quota_metering_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_data import (
    _replace_audit_log_integrity_retention_task_workflow,
    _replace_backup_restore_recovery_task_workflow,
    _replace_cdc_replication_consistency_task_workflow,
    _replace_data_import_validation_task_workflow,
    _replace_data_lifecycle_deletion_retention_task_workflow,
    _replace_database_schema_migration_task_workflow,
    _replace_dsar_data_export_task_workflow,
    _replace_file_upload_storage_safety_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_product import (
    _replace_analytics_experiment_instrumentation_task_workflow,
    _replace_inventory_reservation_consistency_task_workflow,
    _replace_notification_subscription_deliverability_task_workflow,
    _replace_rag_long_chain_task_workflow,
    _replace_schedule_phase_task_workflow,
    _replace_search_index_consistency_task_workflow,
    _replace_search_quality_task_workflow,
    _replace_support_ticket_sla_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_trust import (
    _replace_auth_session_token_lifecycle_task_workflow,
    _replace_authorization_policy_task_workflow,
    _replace_data_residency_task_workflow,
    _replace_identity_sso_task_workflow,
    _replace_key_rotation_task_workflow,
    _replace_kyc_aml_screening_task_workflow,
    _replace_prompt_asset_ownership_task_workflow,
    _replace_support_impersonation_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows import (
    _replace_generic_task_evidence_repair_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_operations import (
    _replace_cache_invalidation_consistency_task_workflow,
    _replace_concurrency_conflict_resolution_task_workflow,
    _replace_feature_flag_rollout_task_workflow,
    _replace_incident_root_cause_task_workflow,
)


TaskWorkflowPredicate = Callable[[str], bool]
TaskWorkflowReplacer = Callable[..., None]


@dataclass(frozen=True)
class TaskWorkflowReplacement:
    predicate: TaskWorkflowPredicate
    replace_workflow: TaskWorkflowReplacer
    passes_task: bool = True


TASK_WORKFLOW_REPLACERS: tuple[TaskWorkflowReplacement, ...] = (
    TaskWorkflowReplacement(_is_prompt_asset_ownership_task, _replace_prompt_asset_ownership_task_workflow),
    TaskWorkflowReplacement(_is_backup_restore_recovery_task, _replace_backup_restore_recovery_task_workflow),
    TaskWorkflowReplacement(_is_audit_log_integrity_retention_task, _replace_audit_log_integrity_retention_task_workflow),
    TaskWorkflowReplacement(_is_database_schema_migration_task, _replace_database_schema_migration_task_workflow),
    TaskWorkflowReplacement(_is_cdc_replication_consistency_task, _replace_cdc_replication_consistency_task_workflow),
    TaskWorkflowReplacement(_is_metric_reporting_reconciliation_task, _replace_metric_reporting_reconciliation_task_workflow),
    TaskWorkflowReplacement(_is_dispute_chargeback_lifecycle_task, _replace_dispute_chargeback_lifecycle_task_workflow),
    TaskWorkflowReplacement(_is_payout_settlement_reconciliation_task, _replace_payout_settlement_reconciliation_task_workflow),
    TaskWorkflowReplacement(_is_analytics_experiment_instrumentation_task, _replace_analytics_experiment_instrumentation_task_workflow),
    TaskWorkflowReplacement(_is_dsar_data_export_task, _replace_dsar_data_export_task_workflow),
    TaskWorkflowReplacement(_is_support_ticket_sla_task, _replace_support_ticket_sla_task_workflow),
    TaskWorkflowReplacement(_is_subscription_entitlement_billing_task, _replace_subscription_entitlement_billing_task_workflow),
    TaskWorkflowReplacement(_is_notification_subscription_deliverability_task, _replace_notification_subscription_deliverability_task_workflow),
    TaskWorkflowReplacement(_is_data_lifecycle_deletion_retention_task, _replace_data_lifecycle_deletion_retention_task_workflow),
    TaskWorkflowReplacement(_is_feature_flag_rollout_task, _replace_feature_flag_rollout_task_workflow),
    TaskWorkflowReplacement(_is_cache_invalidation_consistency_task, _replace_cache_invalidation_consistency_task_workflow),
    TaskWorkflowReplacement(_is_data_import_validation_task, _replace_data_import_validation_task_workflow),
    TaskWorkflowReplacement(_is_concurrency_conflict_resolution_task, _replace_concurrency_conflict_resolution_task_workflow),
    TaskWorkflowReplacement(_is_usage_quota_metering_task, _replace_usage_quota_metering_task_workflow),
    TaskWorkflowReplacement(_is_tax_calculation_compliance_task, _replace_tax_calculation_compliance_task_workflow),
    TaskWorkflowReplacement(_is_inventory_reservation_consistency_task, _replace_inventory_reservation_consistency_task_workflow),
    TaskWorkflowReplacement(_is_file_upload_storage_safety_task, _replace_file_upload_storage_safety_task_workflow),
    TaskWorkflowReplacement(_is_auth_session_token_lifecycle_task, _replace_auth_session_token_lifecycle_task_workflow),
    TaskWorkflowReplacement(_is_rag_long_chain_task, _replace_rag_long_chain_task_workflow, passes_task=False),
    TaskWorkflowReplacement(_is_schedule_phase_task, _replace_schedule_phase_task_workflow, passes_task=False),
    TaskWorkflowReplacement(_is_data_residency_task, _replace_data_residency_task_workflow),
    TaskWorkflowReplacement(_is_support_impersonation_task, _replace_support_impersonation_task_workflow),
    TaskWorkflowReplacement(_is_kyc_aml_screening_task, _replace_kyc_aml_screening_task_workflow),
    TaskWorkflowReplacement(_is_identity_sso_task, _replace_identity_sso_task_workflow),
    TaskWorkflowReplacement(_is_key_rotation_task, _replace_key_rotation_task_workflow),
    TaskWorkflowReplacement(_is_payment_webhook_ledger_task, _replace_payment_webhook_ledger_task_workflow),
    TaskWorkflowReplacement(_is_authorization_policy_task, _replace_authorization_policy_task_workflow),
    TaskWorkflowReplacement(_is_incident_root_cause_task, _replace_incident_root_cause_task_workflow),
    TaskWorkflowReplacement(_is_search_index_consistency_task, _replace_search_index_consistency_task_workflow),
    TaskWorkflowReplacement(_is_search_quality_task, _replace_search_quality_task_workflow, passes_task=False),
)


def _replace_task_anchored_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    for replacement in TASK_WORKFLOW_REPLACERS:
        if replacement.predicate(task):
            _apply_task_workflow_replacement(
                replacement,
                bundle,
                prefers_chinese=prefers_chinese,
                task=task,
                display_language=display_language,
            )
            return
    _replace_generic_task_evidence_repair_workflow(
        bundle,
        prefers_chinese=prefers_chinese,
        task=task,
        display_language=display_language,
    )


def _apply_task_workflow_replacement(
    replacement: TaskWorkflowReplacement,
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    kwargs = {
        "prefers_chinese": prefers_chinese,
        "display_language": display_language,
    }
    if replacement.passes_task:
        kwargs["task"] = task
    replacement.replace_workflow(bundle, **kwargs)
