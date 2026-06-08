from __future__ import annotations

"""Fake-done and evidence-preference traceability categories for Agent candidates."""

import re

from loopora.alignment_traceability_domain_patterns import (
    ACCESSIBILITY_A11Y_PATTERN,
    ANALYTICS_EVENT_INTEGRITY_PATTERN,
    AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
    ASYNC_JOB_LIFECYCLE_PATTERN,
    AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
    BACKUP_RESTORE_RECOVERY_PATTERN,
    BACKWARD_COMPATIBILITY_PATTERN,
    BILLING_LEDGER_RECONCILIATION_PATTERN,
    CACHE_INVALIDATION_CONSISTENCY_PATTERN,
    CDC_REPLICATION_CONSISTENCY_PATTERN,
    CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
    CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
    DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
    DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
    DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
    DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    EVALUATION_SET_PATTERN,
    EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    EXTERNAL_PROVIDER_CONTRACT_PATTERN,
    FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
    FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
    HUMAN_REVIEW_QUALITY_PATTERN,
    IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    IDENTITY_SSO_ASSERTION_PATTERN,
    INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
    INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
    KYC_AML_SANCTIONS_SCREENING_PATTERN,
    KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    LOCALE_I18N_PATTERN,
    METRIC_REPORTING_RECONCILIATION_PATTERN,
    MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
    NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
    PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    QUEUE_FAILURE_RECOVERY_PATTERN,
    RAG_GROUNDING_TOOL_SAFETY_PATTERN,
    REGRESSION_MONITORING_GUARD_PATTERN,
    RESILIENCE_RETRY_TIMEOUT_PATTERN,
    SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    SEARCH_INDEX_CONSISTENCY_PATTERN,
    SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
    SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
    TAX_CALCULATION_COMPLIANCE_PATTERN,
    TENANT_ISOLATION_PATTERN,
    USAGE_QUOTA_METERING_PATTERN,
    WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
)


def agent_candidate_fake_done_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_fake_done_markers = (
        r"\bfake[- ]?(?:done|completion)\b",
        r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b",
        r"\b(?:looks|appears|seems)\s+(?:done|complete|finished|working)\b",
        r"\b(?:only|just|merely)\s+(?:a\s+)?(?:claim|screenshot|download|export|mock|stub|static)\b",
        r"\bhappy[- ]path[- ]only\b",
        r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b",
        r"假完成",
        r"(?:必须|需要|应当|要).{0,16}(?:阻断|拒绝)",
        r"看起来.{0,12}(?:完成|可用|通过)",
        r"(?:不能|不可|不要|不得).{0,16}(?:通过|算完成|收尾)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_fake_done_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "fake-done/blocking",
            r"\bfake[- ]?(?:done|completion)\b|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|假完成|阻断|不得通过|不能通过",
        ),
    ]
    category_patterns = (
        (
            "permission/audit",
            r"\b(?:permission|permissions|authorization|auth|access|acl|access[- ]?control|"
            r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|audit|auditing|audit[- ]?log)\b|"
            r"权限|授权|审计|日志|ACL|权限过滤|访问控制",
            r"\b(?:permission|permissions|authorization|auth|access|acl|access[- ]?control|"
            r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|audit|auditing|audit[- ]?log)\b|"
            r"权限|授权|审计|日志|ACL|权限过滤|访问控制",
        ),
        (
            "access/authorization-policy-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|hide[- ]?button|hidden[- ]?button|middleware|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只隐藏按钮|只加中间件|只检查管理员).{0,220}"
                r"(?:"
                + AUTHORIZATION_POLICY_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + AUTHORIZATION_POLICY_CONSISTENCY_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|hide[- ]?button|hidden[- ]?button|middleware|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只隐藏按钮|只加中间件|只检查管理员)"
            ),
            AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
        ),
        (
            "idempotency/duplicate-prevention",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次)"
                r"|(?:\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            r"\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次",
        ),
        (
            "download/export-only",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
        ),
        (
            "privacy/secrets-redaction",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,100}"
                r"(?:\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证)"
                r"|(?:\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证)"
                r".{0,100}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b"
                r"|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证"
            ),
        ),
        (
            "payment/refund/billing",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "data/export/report",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "migration/rollback-integrity",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过).{0,120}"
                r"(?:"
                + MIGRATION_ROLLBACK_INTEGRITY_PATTERN
                + r")"
                r"|(?:"
                + MIGRATION_ROLLBACK_INTEGRITY_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过)"
            ),
            MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
        ),
        (
            "compatibility/backward-compat",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过).{0,120}"
                r"(?:"
                + BACKWARD_COMPATIBILITY_PATTERN
                + r")"
                r"|(?:"
                + BACKWARD_COMPATIBILITY_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过)"
            ),
            BACKWARD_COMPATIBILITY_PATTERN,
        ),
        (
            "evaluation/eval-set",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,120}"
                r"(?:"
                + EVALUATION_SET_PATTERN
                + r")"
                r"|(?:"
                + EVALUATION_SET_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            EVALUATION_SET_PATTERN,
        ),
        (
            "quality/human-review",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,120}"
                r"(?:"
                + HUMAN_REVIEW_QUALITY_PATTERN
                + r")"
                r"|(?:"
                + HUMAN_REVIEW_QUALITY_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            HUMAN_REVIEW_QUALITY_PATTERN,
        ),
        (
            "ai/rag-grounding-tool-safety",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|demo[- ]?question|plausible[- ]?answer|embedding[- ]?search|ui[- ]?citation(?:s)?|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只让|看起来合理|界面引用|向量搜索|嵌入搜索).{0,220}"
                r"(?:"
                + RAG_GROUNDING_TOOL_SAFETY_PATTERN
                + r")"
                r"|(?:"
                + RAG_GROUNDING_TOOL_SAFETY_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|demo[- ]?question|plausible[- ]?answer|embedding[- ]?search|ui[- ]?citation(?:s)?|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只让|看起来合理|界面引用|向量搜索|嵌入搜索)"
            ),
            RAG_GROUNDING_TOOL_SAFETY_PATTERN,
        ),
        (
            "incident/root-cause-repro",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有|没有).{0,120}"
                r"(?:"
                + INCIDENT_ROOT_CAUSE_REPRO_PATTERN
                + r")"
                r"|(?:"
                + INCIDENT_ROOT_CAUSE_REPRO_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有|没有)"
            ),
            INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
        ),
        (
            "regression/monitoring-guard",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有|没有).{0,120}"
                r"(?:"
                + REGRESSION_MONITORING_GUARD_PATTERN
                + r")"
                r"|(?:"
                + REGRESSION_MONITORING_GUARD_PATTERN
                + r").{0,120}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|拒绝|不得通过|不能通过|只有|没有)"
            ),
            REGRESSION_MONITORING_GUARD_PATTERN,
        ),
        (
            "release/feature-flag-rollout",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|local[- ]?flag|toggle|flag[- ]?toggle|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|本地开关|开关能打开).{0,220}"
                r"(?:"
                + FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN
                + r")"
                r"|(?:"
                + FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|local[- ]?flag|toggle|flag[- ]?toggle|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|本地开关|开关能打开)"
            ),
            FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
        ),
        (
            "external/provider-contract",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,140}"
                r"(?:"
                + EXTERNAL_PROVIDER_CONTRACT_PATTERN
                + r")"
                r"|(?:"
                + EXTERNAL_PROVIDER_CONTRACT_PATTERN
                + r").{0,140}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            EXTERNAL_PROVIDER_CONTRACT_PATTERN,
        ),
        (
            "compliance/kyc-aml-sanctions-screening",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|sandbox[- ]?approved|provider[- ]?status|ui[- ]?verified|"
                r"happy[- ]?path[- ]?webhook|假完成|阻断|拒绝|不得通过|不能通过|只有|沙箱通过|"
                r"供应商状态|界面显示已认证|只跑.*webhook).{0,220}"
                r"(?:"
                + KYC_AML_SANCTIONS_SCREENING_PATTERN
                + r")"
                r"|(?:"
                + KYC_AML_SANCTIONS_SCREENING_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|sandbox[- ]?approved|provider[- ]?status|ui[- ]?verified|"
                r"happy[- ]?path[- ]?webhook|假完成|阻断|拒绝|不得通过|不能通过|只有|沙箱通过|"
                r"供应商状态|界面显示已认证|只跑.*webhook)"
            ),
            KYC_AML_SANCTIONS_SCREENING_PATTERN,
        ),
        (
            "resilience/retry-timeout",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,140}"
                r"(?:"
                + RESILIENCE_RETRY_TIMEOUT_PATTERN
                + r")"
                r"|(?:"
                + RESILIENCE_RETRY_TIMEOUT_PATTERN
                + r").{0,140}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            RESILIENCE_RETRY_TIMEOUT_PATTERN,
        ),
        (
            "access/tenant-isolation",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,140}"
                r"(?:"
                + TENANT_ISOLATION_PATTERN
                + r")"
                r"|(?:"
                + TENANT_ISOLATION_PATTERN
                + r").{0,140}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            TENANT_ISOLATION_PATTERN,
        ),
        (
            "data/residency-regional-isolation",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,180}"
                r"(?:"
                + DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN
                + r")"
                r"|(?:"
                + DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
        ),
        (
            "access/support-impersonation-breakglass",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,180}"
                r"(?:"
                + SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN
                + r")"
                r"|(?:"
                + SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
        ),
        (
            "file-upload/storage-safety",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,180}"
                r"(?:"
                + FILE_UPLOAD_STORAGE_SAFETY_PATTERN
                + r")"
                r"|(?:"
                + FILE_UPLOAD_STORAGE_SAFETY_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
        ),
        (
            "data-import/validation-idempotency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|sample[- ]?csv|all[- ]?rows|假完成|阻断|拒绝|不得通过|不能通过|只有|样例\s*CSV).{0,200}"
                r"(?:"
                + DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN
                + r")"
                r"|(?:"
                + DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN
                + r").{0,200}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|sample[- ]?csv|all[- ]?rows|假完成|阻断|拒绝|不得通过|不能通过|只有|样例\s*CSV)"
            ),
            DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
        ),
        (
            "concurrency/conflict-resolution",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|single[- ]?user|last[- ]?write[- ]?wins?|假完成|阻断|拒绝|不得通过|不能通过|只有|单人保存|最后写入).{0,200}"
                r"(?:"
                + CONCURRENCY_CONFLICT_RESOLUTION_PATTERN
                + r")"
                r"|(?:"
                + CONCURRENCY_CONFLICT_RESOLUTION_PATTERN
                + r").{0,200}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|single[- ]?user|last[- ]?write[- ]?wins?|假完成|阻断|拒绝|不得通过|不能通过|只有|单人保存|最后写入)"
            ),
            CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
        ),
        (
            "inventory/reservation-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|single[- ]?user|single[- ]?checkout|"
                r"ui[- ]?(?:only|shows?|display(?:s|ed)?)|stock[- ]?(?:decrement|reduction)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|单个用户|单次下单|单次结账|"
                r"界面显示|UI\s*显示|库存减少).{0,260}"
                r"(?:"
                + INVENTORY_RESERVATION_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + INVENTORY_RESERVATION_CONSISTENCY_PATTERN
                + r").{0,260}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|single[- ]?user|single[- ]?checkout|"
                r"ui[- ]?(?:only|shows?|display(?:s|ed)?)|stock[- ]?(?:decrement|reduction)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|单个用户|单次下单|单次结账|"
                r"界面显示|UI\s*显示|库存减少)"
            ),
            INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
        ),
        (
            "usage/quota-metering",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|dashboard[- ]?(?:only|shows?|display(?:s|ed)?)|"
                r"single[- ]?(?:api[- ]?)?call|single[- ]?request|429|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|看板显示|dashboard\s*显示|"
                r"单次调用|单个请求|一次调用).{0,300}"
                r"(?:"
                + USAGE_QUOTA_METERING_PATTERN
                + r")"
                r"|(?:"
                + USAGE_QUOTA_METERING_PATTERN
                + r").{0,300}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|dashboard[- ]?(?:only|shows?|display(?:s|ed)?)|"
                r"single[- ]?(?:api[- ]?)?call|single[- ]?request|429|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|看板显示|dashboard\s*显示|"
                r"单次调用|单个请求|一次调用)"
            ),
            USAGE_QUOTA_METERING_PATTERN,
        ),
        (
            "billing/subscription-entitlement-proration",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|button[- ]?only|checkout[- ]?success|provider[- ]?only|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只做按钮|按钮能点|只信\s*provider|只信\s*checkout).{0,340}"
                r"(?:"
                + SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN
                + r")"
                r"|(?:"
                + SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN
                + r").{0,340}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|button[- ]?only|checkout[- ]?success|provider[- ]?only|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|只做按钮|按钮能点|只信\s*provider|只信\s*checkout)"
            ),
            SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
        ),
        (
            "tax/calculation-compliance",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|checkout[- ]?(?:only|shows?|display(?:s|ed)?)|"
                r"single[- ]?(?:tax[- ]?)?rate|one[- ]?rate|provider[- ]?rate|tax[- ]?number|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|checkout\s*显示|显示税费|一个税率|"
                r"一个 tax|provider\s*返回|供应商返回).{0,320}"
                r"(?:"
                + TAX_CALCULATION_COMPLIANCE_PATTERN
                + r")"
                r"|(?:"
                + TAX_CALCULATION_COMPLIANCE_PATTERN
                + r").{0,320}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|checkout[- ]?(?:only|shows?|display(?:s|ed)?)|"
                r"single[- ]?(?:tax[- ]?)?rate|one[- ]?rate|provider[- ]?rate|tax[- ]?number|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|checkout\s*显示|显示税费|一个税率|"
                r"一个 tax|provider\s*返回|供应商返回)"
            ),
            TAX_CALCULATION_COMPLIANCE_PATTERN,
        ),
        (
            "backup/restore-recovery",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|backup[- ]?job[- ]?(?:only|green|success(?:ful)?)|"
                r"snapshot[- ]?(?:file|created|exists)|dashboard[- ]?(?:green|only)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|备份任务成功|备份作业成功|"
                r"生成快照|快照文件|dashboard\s*绿色|看板绿色).{0,320}"
                r"(?:"
                + BACKUP_RESTORE_RECOVERY_PATTERN
                + r")"
                r"|(?:"
                + BACKUP_RESTORE_RECOVERY_PATTERN
                + r").{0,320}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|backup[- ]?job[- ]?(?:only|green|success(?:ful)?)|"
                r"snapshot[- ]?(?:file|created|exists)|dashboard[- ]?(?:green|only)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|备份任务成功|备份作业成功|"
                r"生成快照|快照文件|dashboard\s*绿色|看板绿色)"
            ),
            BACKUP_RESTORE_RECOVERY_PATTERN,
        ),
        (
            "data/cdc-replication-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|sync[- ]?job[- ]?(?:green|success(?:ful)?|only)|"
                r"sample(?:d)?[- ]?row[- ]?count|dashboard[- ]?(?:latest|green|only)|latest[- ]?dashboard|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|同步任务绿色|抽样行数|看板显示|dashboard\s*显示).{0,420}"
                r"(?:"
                + CDC_REPLICATION_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + CDC_REPLICATION_CONSISTENCY_PATTERN
                + r").{0,420}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|sync[- ]?job[- ]?(?:green|success(?:ful)?|only)|"
                r"sample(?:d)?[- ]?row[- ]?count|dashboard[- ]?(?:latest|green|only)|latest[- ]?dashboard|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|同步任务绿色|抽样行数|看板显示|dashboard\s*显示)"
            ),
            CDC_REPLICATION_CONSISTENCY_PATTERN,
        ),
        (
            "audit/log-integrity-retention",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|database[- ]?(?:row|record|table)|"
                r"db[- ]?(?:row|record)|console[- ]?log|ui[- ]?history|history[- ]?row|activity[- ]?row|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|数据库表|一行记录|console\\s*log|"
                r"控制台日志|UI\\s*history|历史记录|操作记录).{0,360}"
                r"(?:"
                + AUDIT_LOG_INTEGRITY_RETENTION_PATTERN
                + r")"
                r"|(?:"
                + AUDIT_LOG_INTEGRITY_RETENTION_PATTERN
                + r").{0,360}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|database[- ]?(?:row|record|table)|"
                r"db[- ]?(?:row|record)|console[- ]?log|ui[- ]?history|history[- ]?row|activity[- ]?row|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|数据库表|一行记录|console\\s*log|"
                r"控制台日志|UI\\s*history|历史记录|操作记录)"
            ),
            AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
        ),
        (
            "cache/invalidation-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|manual[- ]?refresh|database[- ]?update|db[- ]?update|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|手动刷新|数据库更新).{0,220}"
                r"(?:"
                + CACHE_INVALIDATION_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + CACHE_INVALIDATION_CONSISTENCY_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|manual[- ]?refresh|database[- ]?update|db[- ]?update|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|手动刷新|数据库更新)"
            ),
            CACHE_INVALIDATION_CONSISTENCY_PATTERN,
        ),
        (
            "search/index-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|local[- ]?search|public[- ]?document|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|本地搜索|公开文档|搜到一个).{0,260}"
                r"(?:"
                + SEARCH_INDEX_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + SEARCH_INDEX_CONSISTENCY_PATTERN
                + r").{0,260}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|local[- ]?search|public[- ]?document|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|本地搜索|公开文档|搜到一个)"
            ),
            SEARCH_INDEX_CONSISTENCY_PATTERN,
        ),
        (
            "data-lifecycle/deletion-retention",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,160}"
                r"(?:"
                + DATA_LIFECYCLE_DELETION_RETENTION_PATTERN
                + r")"
                r"|(?:"
                + DATA_LIFECYCLE_DELETION_RETENTION_PATTERN
                + r").{0,160}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
        ),
        (
            "privacy/consent-preference-governance",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|banner|checkbox|localstorage|假完成|阻断|拒绝|不得通过|不能通过|只有).{0,180}"
                r"(?:"
                + CONSENT_PREFERENCE_GOVERNANCE_PATTERN
                + r")"
                r"|(?:"
                + CONSENT_PREFERENCE_GOVERNANCE_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|banner|checkbox|localstorage|假完成|阻断|拒绝|不得通过|不能通过|只有)"
            ),
            CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
        ),
        (
            "analytics/event-integrity",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|console\.log|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,160}"
                r"(?:"
                + ANALYTICS_EVENT_INTEGRITY_PATTERN
                + r")"
                r"|(?:"
                + ANALYTICS_EVENT_INTEGRITY_PATTERN
                + r").{0,160}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|console\.log|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            ANALYTICS_EVENT_INTEGRITY_PATTERN,
        ),
        (
            "experiment/assignment-consistency",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,160}"
                r"(?:"
                + EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN
                + r")"
                r"|(?:"
                + EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN
                + r").{0,160}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
        ),
        (
            "async/job-lifecycle",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,160}"
                r"(?:"
                + ASYNC_JOB_LIFECYCLE_PATTERN
                + r")"
                r"|(?:"
                + ASYNC_JOB_LIFECYCLE_PATTERN
                + r").{0,160}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            ASYNC_JOB_LIFECYCLE_PATTERN,
        ),
        (
            "queue/failure-recovery",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,160}"
                r"(?:"
                + QUEUE_FAILURE_RECOVERY_PATTERN
                + r")"
                r"|(?:"
                + QUEUE_FAILURE_RECOVERY_PATTERN
                + r").{0,160}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            QUEUE_FAILURE_RECOVERY_PATTERN,
        ),
        (
            "schedule/timezone-recurrence",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|cron|local[- ]?only|假完成|阻断|拒绝|不得通过|不能通过|只有|本地触发一次).{0,180}"
                r"(?:"
                + SCHEDULE_TIMEZONE_RECURRENCE_PATTERN
                + r")"
                r"|(?:"
                + SCHEDULE_TIMEZONE_RECURRENCE_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|cron|local[- ]?only|假完成|阻断|拒绝|不得通过|不能通过|只有|本地触发一次)"
            ),
            SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
        ),
        (
            "webhook/signature-replay-ordering",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,180}"
                r"(?:"
                + WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN
                + r")"
                r"|(?:"
                + WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
        ),
        (
            "billing/ledger-reconciliation",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,180}"
                r"(?:"
                + BILLING_LEDGER_RECONCILIATION_PATTERN
                + r")"
                r"|(?:"
                + BILLING_LEDGER_RECONCILIATION_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            BILLING_LEDGER_RECONCILIATION_PATTERN,
        ),
        (
            "payment/dispute-chargeback-lifecycle",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|stripe[- ]?dashboard|provider[- ]?dispute[- ]?id|ui[- ]?status|"
                r"happy[- ]?path[- ]?close|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有|"
                r"只存.*争议|只保存.*争议|只改.*状态|dashboard|看.*won|看.*lost).{0,220}"
                r"(?:"
                + DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN
                + r")"
                r"|(?:"
                + DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|stripe[- ]?dashboard|provider[- ]?dispute[- ]?id|ui[- ]?status|"
                r"happy[- ]?path[- ]?close|happy[- ]?path|假完成|阻断|拒绝|不得通过|不能通过|只有|"
                r"只存.*争议|只保存.*争议|只改.*状态|dashboard|看.*won|看.*lost)"
            ),
            DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
        ),
        (
            "payout/settlement-reconciliation",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|stripe[- ]?dashboard[- ]?(?:paid|shows?)|"
                r"provider[- ]?dashboard[- ]?(?:paid|shows?)|test[- ]?payout|single[- ]?payout|"
                r"ui[- ]?(?:balance|shows?|decreas(?:e|ed))|balance[- ]?decreas(?:e|ed)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|Stripe\\s*dashboard|供应商看板|"
                r"一笔测试打款|单笔打款|测试打款|UI\\s*显示余额|余额减少).{0,420}"
                r"(?:"
                + PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN
                + r")"
                r"|(?:"
                + PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN
                + r").{0,420}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|stripe[- ]?dashboard[- ]?(?:paid|shows?)|"
                r"provider[- ]?dashboard[- ]?(?:paid|shows?)|test[- ]?payout|single[- ]?payout|"
                r"ui[- ]?(?:balance|shows?|decreas(?:e|ed))|balance[- ]?decreas(?:e|ed)|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|Stripe\\s*dashboard|供应商看板|"
                r"一笔测试打款|单笔打款|测试打款|UI\\s*显示余额|余额减少)"
            ),
            PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
        ),
        (
            "reporting/metric-reconciliation",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|chart[- ]?only|chart[- ]?render(?:s|ed)?|csv|export|"
                r"dashboard[- ]?only|number(?:s)?[- ]?display|假完成|阻断|拒绝|不得通过|不能通过|只有|"
                r"图表|数字|能导出|导出).{0,420}"
                r"(?:"
                + METRIC_REPORTING_RECONCILIATION_PATTERN
                + r")"
                r"|(?:"
                + METRIC_REPORTING_RECONCILIATION_PATTERN
                + r").{0,420}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|chart[- ]?only|chart[- ]?render(?:s|ed)?|csv|export|"
                r"dashboard[- ]?only|number(?:s)?[- ]?display|假完成|阻断|拒绝|不得通过|不能通过|只有|"
                r"图表|数字|能导出|导出)"
            ),
            METRIC_REPORTING_RECONCILIATION_PATTERN,
        ),
        (
            "identity/sso-assertion",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,180}"
                r"(?:"
                + IDENTITY_SSO_ASSERTION_PATTERN
                + r")"
                r"|(?:"
                + IDENTITY_SSO_ASSERTION_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            IDENTITY_SSO_ASSERTION_PATTERN,
        ),
        (
            "identity/provisioning-role-mapping",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟).{0,180}"
                r"(?:"
                + IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN
                + r")"
                r"|(?:"
                + IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN
                + r").{0,180}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|mock|stub|假完成|阻断|拒绝|不得通过|不能通过|只有|模拟)"
            ),
            IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
        ),
        (
            "auth/session-token-lifecycle",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|email[- ]?sent|link[- ]?sent|reset[- ]?email|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|邮件发出|重置邮件|链接发出).{0,220}"
                r"(?:"
                + AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN
                + r")"
                r"|(?:"
                + AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|email[- ]?sent|link[- ]?sent|reset[- ]?email|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|邮件发出|重置邮件|链接发出)"
            ),
            AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
        ),
        (
            "security/key-rotation-lifecycle",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|ui|env(?:ironment)?[- ]?var(?:iable)?|new[- ]?key|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|新密钥|环境变量|页面显示).{0,220}"
                r"(?:"
                + KEY_ROTATION_SECRET_LIFECYCLE_PATTERN
                + r")"
                r"|(?:"
                + KEY_ROTATION_SECRET_LIFECYCLE_PATTERN
                + r").{0,220}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|"
                r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:must|should|needs?\s+to)\s+(?:block|be\s+blocked|fail|reject)\b|"
                r"\b(?:only|just|merely)\b|happy[- ]?path|ui|env(?:ironment)?[- ]?var(?:iable)?|new[- ]?key|"
                r"假完成|阻断|拒绝|不得通过|不能通过|只有|新密钥|环境变量|页面显示)"
            ),
            KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
        ),
        (
            "notification/subscription-deliverability",
            NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
            NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
        ),
        (
            "visual/polish/screenshot-only",
            r"\b(?:screenshot|visual|polish|pretty|polished-looking)\b|截图|视觉|美化|漂亮",
            r"\b(?:screenshot|visual|polish|pretty|polished-looking)\b|截图|视觉|美化|漂亮",
        ),
        (
            "claim/narrative-only",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
        ),
        (
            "happy-path-only",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
        ),
        (
            "mock/static/stub-only",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
        ),
        (
            "accessibility/a11y",
            ACCESSIBILITY_A11Y_PATTERN,
            ACCESSIBILITY_A11Y_PATTERN,
        ),
        (
            "locale/i18n",
            LOCALE_I18N_PATTERN,
            LOCALE_I18N_PATTERN,
        ),
    )
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in category_patterns
        if re.search(task_pattern, text, re.IGNORECASE)
    )
    return categories


def agent_candidate_evidence_preference_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_evidence_markers = (
        r"\b(?:evidence|proof|verification|verify)\b.{0,80}\b(?:must|should|prefer|include|require|needs?)\b",
        r"\b(?:must|should|prefer|include|require|needs?)\b.{0,80}\b(?:evidence|proof|verification|verify)\b",
        r"证据.{0,24}(?:必须|需要|优先|包括|包含)",
        r"(?:必须|需要|优先|包括|包含).{0,24}(?:证据|证明|验证)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_evidence_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "evidence/proof",
            r"\b(?:evidence|proof|verify|verification|verified|proven)\b|证据|证明|验证|已证明",
        ),
    ]
    category_patterns = (
        (
            "browser/journey",
            r"\b(?:browser|playwright|journey|end[- ]?to[- ]?end|e2e)\b|浏览器|旅程|端到端",
        ),
        (
            "command/test",
            r"\b(?:command|cli|script|test|tests|pytest|unit|contract|lint|typecheck)\b|命令|脚本|测试|契约|类型检查",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace)\b|审计|日志|账本|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access|acl|access[- ]?control|"
            r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?)\b|权限|授权|访问|ACL|权限过滤|访问控制",
        ),
        (
            "access/authorization-policy-consistency",
            AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "migration/rollback-integrity",
            MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
        ),
        (
            "compatibility/backward-compat",
            BACKWARD_COMPATIBILITY_PATTERN,
        ),
        (
            "evaluation/eval-set",
            EVALUATION_SET_PATTERN,
        ),
        (
            "quality/human-review",
            HUMAN_REVIEW_QUALITY_PATTERN,
        ),
        (
            "ai/rag-grounding-tool-safety",
            RAG_GROUNDING_TOOL_SAFETY_PATTERN,
        ),
        (
            "incident/root-cause-repro",
            INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
        ),
        (
            "regression/monitoring-guard",
            REGRESSION_MONITORING_GUARD_PATTERN,
        ),
        (
            "release/feature-flag-rollout",
            FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
        ),
        (
            "external/provider-contract",
            EXTERNAL_PROVIDER_CONTRACT_PATTERN,
        ),
        (
            "compliance/kyc-aml-sanctions-screening",
            KYC_AML_SANCTIONS_SCREENING_PATTERN,
        ),
        (
            "resilience/retry-timeout",
            RESILIENCE_RETRY_TIMEOUT_PATTERN,
        ),
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
        (
            "analytics/event-integrity",
            ANALYTICS_EVENT_INTEGRITY_PATTERN,
        ),
        (
            "experiment/assignment-consistency",
            EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
        ),
        (
            "async/job-lifecycle",
            ASYNC_JOB_LIFECYCLE_PATTERN,
        ),
        (
            "queue/failure-recovery",
            QUEUE_FAILURE_RECOVERY_PATTERN,
        ),
        (
            "schedule/timezone-recurrence",
            SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
        ),
        (
            "webhook/signature-replay-ordering",
            WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
        ),
        (
            "billing/ledger-reconciliation",
            BILLING_LEDGER_RECONCILIATION_PATTERN,
        ),
        (
            "payment/dispute-chargeback-lifecycle",
            DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
        ),
        (
            "payout/settlement-reconciliation",
            PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
        ),
        (
            "reporting/metric-reconciliation",
            METRIC_REPORTING_RECONCILIATION_PATTERN,
        ),
        (
            "identity/sso-assertion",
            IDENTITY_SSO_ASSERTION_PATTERN,
        ),
        (
            "identity/provisioning-role-mapping",
            IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
        ),
        (
            "auth/session-token-lifecycle",
            AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
        ),
        (
            "security/key-rotation-lifecycle",
            KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
        ),
        (
            "notification/subscription-deliverability",
            NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
        ),
        (
            "artifact/ref",
            r"\b(?:artifact|artifacts|file|files|ref|refs|report)\b|产物|文件|引用|报告",
        ),
        (
            "idempotency/duplicate-prevention",
            r"\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次",
        ),
        (
            "privacy/secrets-redaction",
            (
                r"\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b"
                r"|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证"
            ),
        ),
        (
            "accessibility/a11y",
            ACCESSIBILITY_A11Y_PATTERN,
        ),
        (
            "locale/i18n",
            LOCALE_I18N_PATTERN,
        ),
        (
            "screenshot-is-weak",
            r"\b(?:screenshot|screenshots)\b|截图",
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE))
    return categories
