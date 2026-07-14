from __future__ import annotations

from functools import lru_cache
import json

from loopora.alignment_guidance import alignment_guidance_dir
from loopora.service_types import LooporaError

AGREEMENT_READINESS_EVIDENCE_FACTORIES: tuple[tuple[str, str], ...] = (
    ("analytics_experiment_instrumentation", "_analytics_experiment_instrumentation_readiness_evidence"),
    ("audit_log_integrity_retention", "_audit_log_integrity_retention_readiness_evidence"),
    ("auth_session_token_lifecycle", "_auth_session_token_lifecycle_readiness_evidence"),
    ("authorization_policy", "_authorization_policy_readiness_evidence"),
    ("backup_restore_recovery", "_backup_restore_recovery_readiness_evidence"),
    ("cache_invalidation_consistency", "_cache_invalidation_consistency_readiness_evidence"),
    ("cdc_replication_consistency", "_cdc_replication_consistency_readiness_evidence"),
    ("concurrency_conflict_resolution", "_concurrency_conflict_resolution_readiness_evidence"),
    ("data_import_validation", "_data_import_validation_readiness_evidence"),
    ("data_lifecycle_deletion_retention", "_data_lifecycle_deletion_retention_readiness_evidence"),
    ("data_residency", "_data_residency_readiness_evidence"),
    ("database_schema_migration", "_database_schema_migration_readiness_evidence"),
    ("dispute_chargeback_lifecycle", "_dispute_chargeback_lifecycle_readiness_evidence"),
    ("dsar_data_export", "_dsar_data_export_readiness_evidence"),
    ("feature_flag_rollout", "_feature_flag_rollout_readiness_evidence"),
    ("file_upload_storage_safety", "_file_upload_storage_safety_readiness_evidence"),
    ("identity_sso", "_identity_sso_readiness_evidence"),
    ("incident_root_cause", "_incident_root_cause_readiness_evidence"),
    ("inventory_reservation_consistency", "_inventory_reservation_consistency_readiness_evidence"),
    ("key_rotation", "_key_rotation_readiness_evidence"),
    ("kyc_aml_screening", "_kyc_aml_screening_readiness_evidence"),
    ("metric_reporting_reconciliation", "_metric_reporting_reconciliation_readiness_evidence"),
    ("notification_subscription_deliverability", "_notification_subscription_deliverability_readiness_evidence"),
    ("payment_webhook_ledger", "_payment_webhook_ledger_readiness_evidence"),
    ("payout_settlement_reconciliation", "_payout_settlement_reconciliation_readiness_evidence"),
    ("prompt_asset_ownership", "_prompt_asset_ownership_readiness_evidence"),
    ("rag_long_chain", "_rag_long_chain_readiness_evidence"),
    ("refund_repair", "_refund_repair_readiness_evidence"),
    ("schedule_timezone_recurrence", "_schedule_timezone_recurrence_readiness_evidence"),
    ("search_index_consistency", "_search_index_consistency_readiness_evidence"),
    ("search_quality", "_search_quality_readiness_evidence"),
    ("search_refactor_improvement", "_search_refactor_improvement_readiness_evidence"),
    ("subscription_entitlement_billing", "_subscription_entitlement_billing_readiness_evidence"),
    ("support_impersonation", "_support_impersonation_readiness_evidence"),
    ("support_ticket_sla", "_support_ticket_sla_readiness_evidence"),
    ("tax_calculation_compliance", "_tax_calculation_compliance_readiness_evidence"),
    ("usage_quota_metering", "_usage_quota_metering_readiness_evidence"),
)


def _agreement_readiness_evidence_factory(fixture_key: str, function_name: str):
    def _readiness_evidence(task: str, *, language: str) -> dict:
        return _agreement_readiness_evidence_from_asset(fixture_key, task, language=language)

    _readiness_evidence.__name__ = function_name
    _readiness_evidence.__qualname__ = function_name
    return _readiness_evidence


for _fixture_key, _function_name in AGREEMENT_READINESS_EVIDENCE_FACTORIES:
    globals()[_function_name] = _agreement_readiness_evidence_factory(_fixture_key, _function_name)

del _fixture_key, _function_name


def _agreement_readiness_evidence_from_asset(fixture_key: str, task: str, *, language: str) -> dict:
    locale = _agreement_readiness_locale(language)
    fixture = _agreement_readiness_evidence_asset().get("tasks", {}).get(fixture_key)
    if not isinstance(fixture, dict):
        raise LooporaError(f"missing agreement readiness evidence fixture: {fixture_key}")
    localized = fixture.get(locale) or fixture.get("en")
    if not isinstance(localized, dict):
        raise LooporaError(f"agreement readiness evidence fixture missing locale: {fixture_key}/{locale}")
    task_text = str(task or "")
    evidence: dict[str, str] = {}
    for key, value in localized.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, str):
            raise LooporaError(f"invalid agreement readiness evidence field: {fixture_key}/{locale}")
        evidence[key] = value.replace("{task}", task_text)
    return evidence


def _agreement_readiness_locale(language: str) -> str:
    locale = str(language or "").strip().lower()
    if locale == "zh":
        return "zh"
    if locale == "es":
        return "es"
    return "en"


@lru_cache(maxsize=1)
def _agreement_readiness_evidence_asset() -> dict:
    path = alignment_guidance_dir() / "agreement-readiness-evidence.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LooporaError("invalid agreement readiness evidence asset") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), dict):
        raise LooporaError("agreement readiness evidence asset must define tasks")
    return payload
