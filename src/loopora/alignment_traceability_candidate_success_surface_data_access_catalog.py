from __future__ import annotations

"""Agent-candidate success-surface data, access, and consistency categories."""

from loopora.alignment_traceability_domain_patterns import (
    AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
    BACKUP_RESTORE_RECOVERY_PATTERN,
    CACHE_INVALIDATION_CONSISTENCY_PATTERN,
    CDC_REPLICATION_CONSISTENCY_PATTERN,
    CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
    CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
    DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
    DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
    DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
    FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
    INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
    SEARCH_INDEX_CONSISTENCY_PATTERN,
    SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
    SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
    TAX_CALCULATION_COMPLIANCE_PATTERN,
    TENANT_ISOLATION_PATTERN,
    USAGE_QUOTA_METERING_PATTERN,
)

SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS = (
    (
        "access/tenant-isolation",
        TENANT_ISOLATION_PATTERN,
    ),
    (
        "data/residency-regional-isolation",
        DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
    ),
    (
        "access/support-impersonation-breakglass",
        SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
    ),
    (
        "file-upload/storage-safety",
        FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
    ),
    (
        "data-import/validation-idempotency",
        DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
    ),
    (
        "concurrency/conflict-resolution",
        CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
    ),
    (
        "inventory/reservation-consistency",
        INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
    ),
    (
        "usage/quota-metering",
        USAGE_QUOTA_METERING_PATTERN,
    ),
    (
        "billing/subscription-entitlement-proration",
        SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
    ),
    (
        "tax/calculation-compliance",
        TAX_CALCULATION_COMPLIANCE_PATTERN,
    ),
    (
        "backup/restore-recovery",
        BACKUP_RESTORE_RECOVERY_PATTERN,
    ),
    (
        "data/cdc-replication-consistency",
        CDC_REPLICATION_CONSISTENCY_PATTERN,
    ),
    (
        "audit/log-integrity-retention",
        AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
    ),
    (
        "cache/invalidation-consistency",
        CACHE_INVALIDATION_CONSISTENCY_PATTERN,
    ),
    (
        "search/index-consistency",
        SEARCH_INDEX_CONSISTENCY_PATTERN,
    ),
    (
        "data-lifecycle/deletion-retention",
        DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
    ),
    (
        "privacy/consent-preference-governance",
        CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
    ),
)

__all__ = ("SUCCESS_SURFACE_DATA_ACCESS_CATEGORY_PATTERNS",)
