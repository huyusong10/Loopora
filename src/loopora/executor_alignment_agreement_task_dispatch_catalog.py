from __future__ import annotations

from loopora.executor_alignment_agreement_task_dispatch_commercial import COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES
from loopora.executor_alignment_agreement_task_dispatch_data import DATA_TASK_AGREEMENT_FACTORY_ROUTES
from loopora.executor_alignment_agreement_task_dispatch_operations import OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES
from loopora.executor_alignment_agreement_task_dispatch_product import PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES
from loopora.executor_alignment_agreement_task_dispatch_trust import TRUST_TASK_AGREEMENT_FACTORY_ROUTES
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

TASK_AGREEMENT_FACTORIES: tuple[AgreementTaskFactoryRoute, ...] = (
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["prompt_asset_ownership"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["backup_restore_recovery"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["audit_log_integrity_retention"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["database_schema_migration"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["cdc_replication_consistency"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["metric_reporting_reconciliation"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["dispute_chargeback_lifecycle"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["payout_settlement_reconciliation"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["analytics_experiment_instrumentation"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["schedule_timezone_recurrence"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["dsar_data_export"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["support_ticket_sla"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["subscription_entitlement_billing"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["notification_subscription_deliverability"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["data_lifecycle_deletion_retention"],
    OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES["feature_flag_rollout"],
    OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES["cache_invalidation_consistency"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["data_import_validation"],
    OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES["concurrency_conflict_resolution"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["usage_quota_metering"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["tax_calculation_compliance"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["inventory_reservation_consistency"],
    DATA_TASK_AGREEMENT_FACTORY_ROUTES["file_upload_storage_safety"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["auth_session_token_lifecycle"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["data_residency"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["support_impersonation"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["kyc_aml_screening"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["identity_sso"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["key_rotation"],
    COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["payment_webhook_ledger"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["rag_long_chain"],
    TRUST_TASK_AGREEMENT_FACTORY_ROUTES["authorization_policy"],
    OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES["incident_root_cause"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["search_index_consistency"],
    PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["search_quality"],
)
