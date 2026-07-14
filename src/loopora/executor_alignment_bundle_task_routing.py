from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from loopora.executor_alignment_bundle_task_spec_scaffolds_commercial import (
    _append_payment_webhook_ledger_spec_notes,
    _append_metric_reporting_reconciliation_spec_notes,
    _append_usage_quota_metering_spec_notes,
    _append_subscription_entitlement_billing_spec_notes,
    _append_tax_calculation_compliance_spec_notes,
)
from loopora.executor_alignment_bundle_task_spec_scaffolds_data import (
    _append_backup_restore_recovery_spec_notes,
    _append_audit_log_integrity_retention_spec_notes,
    _append_database_schema_migration_spec_notes,
    _append_cdc_replication_consistency_spec_notes,
    _append_data_lifecycle_deletion_retention_spec_notes,
    _append_cache_invalidation_consistency_spec_notes,
    _append_data_import_validation_spec_notes,
    _append_dsar_data_export_spec_notes,
    _append_file_upload_storage_safety_spec_notes,
)
from loopora.executor_alignment_bundle_task_spec_scaffolds_operations import (
    _append_feature_flag_rollout_spec_notes,
    _append_incident_root_cause_spec_notes,
)
from loopora.executor_alignment_bundle_task_spec_scaffolds_product import (
    _append_schedule_phase_spec_notes,
    _append_search_index_consistency_spec_notes,
    _append_search_quality_spec_notes,
    _append_concurrency_conflict_resolution_spec_notes,
    _append_rag_long_chain_spec_notes,
    _append_notification_subscription_deliverability_spec_notes,
    _append_analytics_experiment_instrumentation_spec_notes,
    _append_support_ticket_sla_spec_notes,
    _append_inventory_reservation_consistency_spec_notes,
)
from loopora.executor_alignment_bundle_task_spec_scaffolds_trust import (
    _append_authorization_policy_spec_notes,
    _append_data_residency_spec_notes,
    _append_support_impersonation_spec_notes,
    _append_kyc_aml_screening_spec_notes,
    _append_identity_sso_spec_notes,
    _append_key_rotation_spec_notes,
    _append_prompt_asset_ownership_spec_notes,
    _append_auth_session_token_lifecycle_spec_notes,
)


TaskSpecNoteAppender = Callable[..., None]


@dataclass(frozen=True)
class TaskSpecNoteAppenderRegistration:
    preset: str
    append_notes: TaskSpecNoteAppender


TASK_SPEC_NOTE_APPENDERS: tuple[TaskSpecNoteAppenderRegistration, ...] = (
    TaskSpecNoteAppenderRegistration("rag-grounding-long-chain", _append_rag_long_chain_spec_notes),
    TaskSpecNoteAppenderRegistration("schedule-timezone-contract-parallel-recurrence", _append_schedule_phase_spec_notes),
    TaskSpecNoteAppenderRegistration("search-quality-evaluation", _append_search_quality_spec_notes),
    TaskSpecNoteAppenderRegistration("search-index-contract-parallel-consistency", _append_search_index_consistency_spec_notes),
    TaskSpecNoteAppenderRegistration("prompt-asset-ownership-contract-parallel-rendering", _append_prompt_asset_ownership_spec_notes),
    TaskSpecNoteAppenderRegistration("backup-restore-contract-parallel-recovery", _append_backup_restore_recovery_spec_notes),
    TaskSpecNoteAppenderRegistration("audit-log-integrity-contract-parallel-retention", _append_audit_log_integrity_retention_spec_notes),
    TaskSpecNoteAppenderRegistration("dsar-export-contract-parallel-privacy", _append_dsar_data_export_spec_notes),
    TaskSpecNoteAppenderRegistration("support-ticket-contract-parallel-sla", _append_support_ticket_sla_spec_notes),
    TaskSpecNoteAppenderRegistration("subscription-entitlement-contract-parallel-billing", _append_subscription_entitlement_billing_spec_notes),
    TaskSpecNoteAppenderRegistration("notification-subscription-contract-parallel-deliverability", _append_notification_subscription_deliverability_spec_notes),
    TaskSpecNoteAppenderRegistration("analytics-experiment-contract-parallel-instrumentation", _append_analytics_experiment_instrumentation_spec_notes),
    TaskSpecNoteAppenderRegistration("database-schema-migration-contract-parallel-backfill", _append_database_schema_migration_spec_notes),
    TaskSpecNoteAppenderRegistration("cdc-replication-contract-parallel-consistency", _append_cdc_replication_consistency_spec_notes),
    TaskSpecNoteAppenderRegistration("metric-reporting-contract-parallel-reconciliation", _append_metric_reporting_reconciliation_spec_notes),
    TaskSpecNoteAppenderRegistration("data-lifecycle-contract-parallel-deletion-retention", _append_data_lifecycle_deletion_retention_spec_notes),
    TaskSpecNoteAppenderRegistration("feature-flag-rollout-contract-parallel-release", _append_feature_flag_rollout_spec_notes),
    TaskSpecNoteAppenderRegistration("cache-invalidation-contract-parallel-consistency", _append_cache_invalidation_consistency_spec_notes),
    TaskSpecNoteAppenderRegistration("data-import-contract-parallel-validation", _append_data_import_validation_spec_notes),
    TaskSpecNoteAppenderRegistration("collaborative-conflict-contract-parallel-resolution", _append_concurrency_conflict_resolution_spec_notes),
    TaskSpecNoteAppenderRegistration("usage-quota-contract-parallel-metering", _append_usage_quota_metering_spec_notes),
    TaskSpecNoteAppenderRegistration("tax-calculation-contract-parallel-compliance", _append_tax_calculation_compliance_spec_notes),
    TaskSpecNoteAppenderRegistration("inventory-reservation-contract-parallel-consistency", _append_inventory_reservation_consistency_spec_notes),
    TaskSpecNoteAppenderRegistration("file-upload-contract-parallel-storage-safety", _append_file_upload_storage_safety_spec_notes),
    TaskSpecNoteAppenderRegistration("auth-session-token-contract-parallel-lifecycle", _append_auth_session_token_lifecycle_spec_notes),
    TaskSpecNoteAppenderRegistration("data-residency-contract-first", _append_data_residency_spec_notes),
    TaskSpecNoteAppenderRegistration("support-impersonation-policy-first", _append_support_impersonation_spec_notes),
    TaskSpecNoteAppenderRegistration("kyc-aml-compliance-parallel-controls", _append_kyc_aml_screening_spec_notes),
    TaskSpecNoteAppenderRegistration("identity-sso-contract-parallel-controls", _append_identity_sso_spec_notes),
    TaskSpecNoteAppenderRegistration("key-rotation-contract-parallel-controls", _append_key_rotation_spec_notes),
    TaskSpecNoteAppenderRegistration("payment-webhook-contract-parallel-controls", _append_payment_webhook_ledger_spec_notes),
    TaskSpecNoteAppenderRegistration("authorization-policy-parallel-inspection", _append_authorization_policy_spec_notes),
    TaskSpecNoteAppenderRegistration("incident-root-cause-repro", _append_incident_root_cause_spec_notes),
)


def _append_selected_workflow_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    preset = str(workflow.get("preset") or "")
    for registration in TASK_SPEC_NOTE_APPENDERS:
        if registration.preset == preset:
            registration.append_notes(
                bundle,
                prefers_chinese=prefers_chinese,
                task=task,
                display_language=display_language,
            )
            return
