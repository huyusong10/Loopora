from __future__ import annotations

from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets

TASK_WORKFLOW_INTENTS_ASSET_NAME = "task-workflow-intents.json"
TASK_WORKFLOW_INTENT_REPLACERS: tuple[tuple[str, str], ...] = (
    ("generic_task_evidence_repair", "_replace_generic_task_evidence_repair_workflow_intent"),
    ("data_residency", "_replace_data_residency_task_workflow_intent"),
    ("support_impersonation", "_replace_support_impersonation_task_workflow_intent"),
    ("kyc_aml_screening", "_replace_kyc_aml_screening_task_workflow_intent"),
    ("payment_webhook_ledger", "_replace_payment_webhook_ledger_task_workflow_intent"),
    ("identity_sso", "_replace_identity_sso_task_workflow_intent"),
    ("key_rotation", "_replace_key_rotation_task_workflow_intent"),
    ("prompt_asset_ownership", "_replace_prompt_asset_ownership_task_workflow_intent"),
    ("backup_restore_recovery", "_replace_backup_restore_recovery_task_workflow_intent"),
    ("audit_log_integrity_retention", "_replace_audit_log_integrity_retention_task_workflow_intent"),
    ("notification_subscription_deliverability", "_replace_notification_subscription_deliverability_task_workflow_intent"),
    ("analytics_experiment_instrumentation", "_replace_analytics_experiment_instrumentation_task_workflow_intent"),
    ("database_schema_migration", "_replace_database_schema_migration_task_workflow_intent"),
    ("cdc_replication_consistency", "_replace_cdc_replication_consistency_task_workflow_intent"),
    ("metric_reporting_reconciliation", "_replace_metric_reporting_reconciliation_task_workflow_intent"),
    ("dispute_chargeback_lifecycle", "_replace_dispute_chargeback_lifecycle_task_workflow_intent"),
    ("payout_settlement_reconciliation", "_replace_payout_settlement_reconciliation_task_workflow_intent"),
    ("data_lifecycle_deletion_retention", "_replace_data_lifecycle_deletion_retention_task_workflow_intent"),
    ("feature_flag_rollout", "_replace_feature_flag_rollout_task_workflow_intent"),
    ("cache_invalidation_consistency", "_replace_cache_invalidation_consistency_task_workflow_intent"),
    ("data_import_validation", "_replace_data_import_validation_task_workflow_intent"),
    ("concurrency_conflict_resolution", "_replace_concurrency_conflict_resolution_task_workflow_intent"),
    ("usage_quota_metering", "_replace_usage_quota_metering_task_workflow_intent"),
    ("subscription_entitlement_billing", "_replace_subscription_entitlement_billing_task_workflow_intent"),
    ("dsar_data_export", "_replace_dsar_data_export_task_workflow_intent"),
    ("support_ticket_sla", "_replace_support_ticket_sla_task_workflow_intent"),
    ("tax_calculation_compliance", "_replace_tax_calculation_compliance_task_workflow_intent"),
    ("inventory_reservation_consistency", "_replace_inventory_reservation_consistency_task_workflow_intent"),
    ("file_upload_storage_safety", "_replace_file_upload_storage_safety_task_workflow_intent"),
    ("auth_session_token_lifecycle", "_replace_auth_session_token_lifecycle_task_workflow_intent"),
    ("authorization_policy", "_replace_authorization_policy_task_workflow_intent"),
    ("incident_root_cause", "_replace_incident_root_cause_task_workflow_intent"),
    ("schedule_phase", "_replace_schedule_phase_task_workflow_intent"),
    ("search_index_consistency", "_replace_search_index_consistency_task_workflow_intent"),
    ("search_quality", "_replace_search_quality_task_workflow_intent"),
    ("rag_long_chain", "_replace_rag_long_chain_task_workflow_intent"),
)


def _task_workflow_intent_replacer(intent_key: str, function_name: str):
    def _replace_intent(
        bundle: dict,
        *,
        prefers_chinese: bool,
        display_language: str = "",
    ) -> None:
        _replace_task_workflow_intent(
            bundle,
            intent_key=intent_key,
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )

    _replace_intent.__name__ = function_name
    _replace_intent.__qualname__ = function_name
    return _replace_intent


for _intent_key, _function_name in TASK_WORKFLOW_INTENT_REPLACERS:
    globals()[_function_name] = _task_workflow_intent_replacer(_intent_key, _function_name)

del _intent_key, _function_name


def _replace_task_workflow_intent(
    bundle: dict,
    *,
    intent_key: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    workflow = bundle["workflow"]
    workflow["collaboration_intent"] = _task_workflow_intent(
        intent_key,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def _task_workflow_intent(
    intent_key: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    language = _task_workflow_intent_language(prefers_chinese=prefers_chinese, display_language=display_language)
    intents = _task_workflow_intents_asset()
    localized = intents.get(str(intent_key or ""))
    if not isinstance(localized, dict):
        raise ValueError(f"missing task workflow intent asset: {intent_key}")
    return localized.get(language) or localized["en"]


def _task_workflow_intent_language(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "zh"
    if str(display_language or "").strip().lower() == "es":
        return "es"
    return "en"


@lru_cache
def _task_workflow_intents_asset() -> dict[str, dict[str, str]]:
    asset = load_alignment_guidance_assets().task_workflow_intents
    if not all(isinstance(intent_key, str) and isinstance(localized, dict) for intent_key, localized in asset.items()):
        raise ValueError(f"{TASK_WORKFLOW_INTENTS_ASSET_NAME} must map intent keys to locale maps")
    return {intent_key: _task_workflow_locale_intents(intent_key, localized) for intent_key, localized in asset.items()}


def _task_workflow_locale_intents(intent_key: str, localized: dict[str, Any]) -> dict[str, str]:
    required_locales = ("en", "zh", "es")
    if not all(isinstance(localized.get(locale), str) and localized[locale].strip() for locale in required_locales):
        raise ValueError(f"{TASK_WORKFLOW_INTENTS_ASSET_NAME}.{intent_key} must include en/zh/es intents")
    return {locale: str(localized[locale]).strip() for locale in required_locales}
