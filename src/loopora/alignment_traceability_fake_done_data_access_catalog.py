from __future__ import annotations

"""Fake-done catalog entries for access, data, storage, and consistency proof gaps."""

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

from loopora.alignment_traceability_risk_markers import (
    FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
    risk_marker_near_domain_pattern,
)

FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS = (
    (
        "access/tenant-isolation",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            TENANT_ISOLATION_PATTERN,
            window=140,
        ),
        TENANT_ISOLATION_PATTERN,
    ),
    (
        "data/residency-regional-isolation",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
            window=180,
        ),
        DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
    ),
    (
        "access/support-impersonation-breakglass",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
            window=180,
        ),
        SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
    ),
    (
        "file-upload/storage-safety",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
            window=180,
        ),
        FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
    ),
    (
        "data-import/validation-idempotency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
            window=200,
            extra_marker_pattern=r"sample[- ]?csv|all[- ]?rows|样例\s*CSV",
        ),
        DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
    ),
    (
        "concurrency/conflict-resolution",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
            window=200,
            extra_marker_pattern=r"single[- ]?user|last[- ]?write[- ]?wins?|单人保存|最后写入",
        ),
        CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
    ),
    (
        "inventory/reservation-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
            window=260,
            extra_marker_pattern=(
                r"single[- ]?user|single[- ]?checkout|ui[- ]?(?:only|shows?|display(?:s|ed)?)|"
                r"stock[- ]?(?:decrement|reduction)|单个用户|单次下单|单次结账|界面显示|UI\s*显示|库存减少"
            ),
        ),
        INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
    ),
    (
        "usage/quota-metering",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            USAGE_QUOTA_METERING_PATTERN,
            window=300,
            extra_marker_pattern=(
                r"dashboard[- ]?(?:only|shows?|display(?:s|ed)?)|single[- ]?(?:api[- ]?)?call|"
                r"single[- ]?request|429|看板显示|dashboard\s*显示|单次调用|单个请求|一次调用"
            ),
        ),
        USAGE_QUOTA_METERING_PATTERN,
    ),
    (
        "billing/subscription-entitlement-proration",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
            window=340,
            extra_marker_pattern=(
                r"button[- ]?only|checkout[- ]?success|provider[- ]?only|"
                r"只做按钮|按钮能点|只信\s*provider|只信\s*checkout"
            ),
        ),
        SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
    ),
    (
        "tax/calculation-compliance",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            TAX_CALCULATION_COMPLIANCE_PATTERN,
            window=320,
            extra_marker_pattern=(
                r"checkout[- ]?(?:only|shows?|display(?:s|ed)?)|single[- ]?(?:tax[- ]?)?rate|"
                r"one[- ]?rate|provider[- ]?rate|tax[- ]?number|checkout\s*显示|显示税费|一个税率|"
                r"一个 tax|provider\s*返回|供应商返回"
            ),
        ),
        TAX_CALCULATION_COMPLIANCE_PATTERN,
    ),
    (
        "backup/restore-recovery",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            BACKUP_RESTORE_RECOVERY_PATTERN,
            window=320,
            extra_marker_pattern=(
                r"backup[- ]?job[- ]?(?:only|green|success(?:ful)?)|snapshot[- ]?(?:file|created|exists)|"
                r"dashboard[- ]?(?:green|only)|备份任务成功|备份作业成功|生成快照|快照文件|"
                r"dashboard\s*绿色|看板绿色"
            ),
        ),
        BACKUP_RESTORE_RECOVERY_PATTERN,
    ),
    (
        "data/cdc-replication-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            CDC_REPLICATION_CONSISTENCY_PATTERN,
            window=420,
            extra_marker_pattern=(
                r"sync[- ]?job[- ]?(?:green|success(?:ful)?|only)|sample(?:d)?[- ]?row[- ]?count|"
                r"dashboard[- ]?(?:latest|green|only)|latest[- ]?dashboard|同步任务绿色|抽样行数|"
                r"看板显示|dashboard\s*显示"
            ),
        ),
        CDC_REPLICATION_CONSISTENCY_PATTERN,
    ),
    (
        "audit/log-integrity-retention",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
            window=360,
            extra_marker_pattern=(
                r"database[- ]?(?:row|record|table)|db[- ]?(?:row|record)|console[- ]?log|"
                r"ui[- ]?history|history[- ]?row|activity[- ]?row|数据库表|一行记录|"
                r"console\\s*log|控制台日志|UI\\s*history|历史记录|操作记录"
            ),
        ),
        AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
    ),
    (
        "cache/invalidation-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            CACHE_INVALIDATION_CONSISTENCY_PATTERN,
            window=220,
            extra_marker_pattern=r"manual[- ]?refresh|database[- ]?update|db[- ]?update|手动刷新|数据库更新",
        ),
        CACHE_INVALIDATION_CONSISTENCY_PATTERN,
    ),
    (
        "search/index-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            SEARCH_INDEX_CONSISTENCY_PATTERN,
            window=260,
            extra_marker_pattern=r"local[- ]?search|public[- ]?document|本地搜索|公开文档|搜到一个",
        ),
        SEARCH_INDEX_CONSISTENCY_PATTERN,
    ),
    (
        "data-lifecycle/deletion-retention",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
            window=160,
        ),
        DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
    ),
    (
        "privacy/consent-preference-governance",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
            window=180,
            extra_marker_pattern=r"banner|checkbox|localstorage",
        ),
        CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
    ),
)

__all__ = ("FAKE_DONE_DATA_ACCESS_CATEGORY_PATTERNS",)
